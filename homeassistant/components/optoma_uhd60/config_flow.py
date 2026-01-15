"""Config flow for the Optoma UHD60 integration."""

from __future__ import annotations

import logging
import socket
import telnetlib  # pylint: disable=deprecated-module
from typing import Any

from pypjlink2 import Projector, ProjectorError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CMD_GET_MODEL,
    CMD_GET_SERIAL,
    COMMAND_TERMINATOR,
    DEFAULT_PORT,
    DOMAIN,
    TELNET_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    host = data[CONF_HOST]

    # Test connection using pypjlink2 and get device info via telnet
    def _connect_and_validate() -> dict[str, str]:
        """Connect to projector and retrieve device information."""
        # First, test PJLink connection (used for power control)
        try:
            projector = Projector.from_address(host)
            # Test connection by getting power state
            projector.get_power()
        except (ProjectorError, TimeoutError, OSError) as err:
            _LOGGER.debug("PJLink connection failed to %s: %s", host, err)
            raise CannotConnect from err

        # Then get serial and model via telnet (port 23)
        try:
            tn = telnetlib.Telnet(host, DEFAULT_PORT, timeout=TELNET_TIMEOUT)
        except (ConnectionRefusedError, OSError, socket.timeout) as err:
            _LOGGER.debug(
                "Telnet connection failed to %s:%s: %s", host, DEFAULT_PORT, err
            )
            raise CannotConnect from err

        try:
            # Get serial number
            tn.write((CMD_GET_SERIAL + COMMAND_TERMINATOR).encode("ascii"))
            serial_response = tn.read_until(b"\r", timeout=TELNET_TIMEOUT).decode(
                "ascii"
            ).strip()

            # Get model
            tn.write((CMD_GET_MODEL + COMMAND_TERMINATOR).encode("ascii"))
            model_response = tn.read_until(b"\r", timeout=TELNET_TIMEOUT).decode(
                "ascii"
            ).strip()

            # Clean up responses (remove "OK" prefix if present)
            serial = serial_response.replace("OK", "").strip()
            model = model_response.replace("OK", "").strip()

            if not serial or not model:
                _LOGGER.debug(
                    "Failed to retrieve valid device info via telnet, "
                    "serial_response=%r, model_response=%r",
                    serial_response,
                    model_response,
                )
                raise CannotConnect(
                    "Failed to retrieve device serial number or model via telnet"
                )

            return {"serial": serial, "model": model}

        except (socket.timeout, EOFError, UnicodeDecodeError) as err:
            _LOGGER.debug("Failed to retrieve device info via telnet: %s", err)
            raise CannotConnect from err
        finally:
            try:
                tn.close()
            except Exception as err:  # noqa: S110
                _LOGGER.debug("Failed to close telnet connection: %s", err)

    device_info = await hass.async_add_executor_job(_connect_and_validate)

    # Create title and unique ID
    title = f"{device_info['model']}-{device_info['serial']}"
    unique_id = device_info["serial"]

    return {"title": title, "unique_id": unique_id}


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Optoma UHD60."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Set unique ID and abort if already configured
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
