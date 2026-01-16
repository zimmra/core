"""The Optoma UHD60 integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DEFAULT_PORT
from .projector import OptomaConnectionError, OptomaProjector

_LOGGER = logging.getLogger(__name__)
_PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]

type OptomaUHD60ConfigEntry = ConfigEntry[OptomaProjector]


async def async_setup_entry(hass: HomeAssistant, entry: OptomaUHD60ConfigEntry) -> bool:
    """Set up Optoma UHD60 from a config entry."""
    host = entry.data[CONF_HOST]

    # Create projector client
    projector = OptomaProjector(host, DEFAULT_PORT)

    # Attempt to connect to the projector
    try:
        await projector.connect()
    except OptomaConnectionError as ex:
        raise ConfigEntryNotReady(f"Failed to connect to projector at {host}") from ex

    # Store the projector client in runtime_data
    entry.runtime_data = projector

    # Forward setup to the media_player platform
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: OptomaUHD60ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms first
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, _PLATFORMS):
        # Disconnect from the projector
        await entry.runtime_data.disconnect()

    return unload_ok
