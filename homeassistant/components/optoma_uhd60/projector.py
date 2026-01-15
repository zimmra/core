"""Projector client for Optoma UHD60."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from typing import Any

from pypjlink2 import Projector as PJLinkProjector
from pypjlink2.projector import ProjectorError

from .const import (
    COMMAND_TERMINATOR,
    CMD_GET_BRIGHTNESS,
    CMD_GET_CONTRAST,
    CMD_GET_DISPLAY_MODE,
    CMD_GET_INPUT,
    CMD_GET_LAMP_HOURS,
    CMD_GET_MAC,
    CMD_GET_MODEL,
    CMD_GET_SERIAL,
    CMD_GET_SW_VERSION,
    CMD_NAV_DOWN,
    CMD_NAV_INFO,
    CMD_NAV_LEFT,
    CMD_NAV_MENU,
    CMD_NAV_RIGHT,
    CMD_NAV_SELECT,
    CMD_NAV_UP,
    CMD_RESYNC_HDMI,
    CMD_SET_BRIGHTNESS,
    CMD_SET_BRILLIANT_COLOR,
    CMD_SET_CONTRAST,
    CMD_SET_DISPLAY_BRIGHT,
    CMD_SET_DISPLAY_CINEMA,
    CMD_SET_DISPLAY_FILM,
    CMD_SET_DISPLAY_HDR,
    CMD_SET_DISPLAY_USER,
    CMD_SET_DISPLAY_VIVID,
    CMD_SET_INPUT_HDMI1,
    CMD_SET_INPUT_HDMI2,
    CMD_SET_INPUT_VGA,
    CMD_SET_LAMP_BRIGHT,
    CMD_SET_LAMP_DYNAMIC,
    CMD_SET_LAMP_ECO,
    DEFAULT_PORT,
    DISPLAY_MODE_MAP,
    INPUT_SOURCE_MAP,
    RESPONSE_FAIL,
    RESPONSE_OK,
    RESPONSE_PASS,
    TELNET_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

# PJLink port
PJLINK_PORT = 4352


class OptomaProjectorError(Exception):
    """Base exception for Optoma projector errors."""


class OptomaConnectionError(OptomaProjectorError):
    """Exception for connection errors."""


class OptomaCommandError(OptomaProjectorError):
    """Exception for command execution errors."""


class OptomaProjector:
    """Client for Optoma UHD60 projector."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        password: str | None = None,
    ) -> None:
        """Initialize the projector client."""
        self._host = host
        self._port = port
        self._password = password
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._listeners: list[Callable[[str], None]] = []
        self._monitor_task: asyncio.Task | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._available = False
        self._unavailable_logged = False

    @property
    def available(self) -> bool:
        """Return if the projector is available."""
        return self._available

    @property
    def host(self) -> str:
        """Return the projector host."""
        return self._host

    async def connect(self) -> None:
        """Establish connection to the projector."""
        async with self._lock:
            if self._writer is not None:
                return

            try:
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self._host, self._port),
                    timeout=TELNET_TIMEOUT,
                )
                self._available = True
                if self._unavailable_logged:
                    _LOGGER.info("Connected to projector at %s:%s", self._host, self._port)
                    self._unavailable_logged = False

                # Start monitoring for broadcast messages
                if self._monitor_task is None or self._monitor_task.done():
                    self._monitor_task = asyncio.create_task(self._monitor_broadcasts())

            except (OSError, asyncio.TimeoutError) as ex:
                self._available = False
                if not self._unavailable_logged:
                    _LOGGER.info(
                        "Unable to connect to projector at %s:%s: %s",
                        self._host,
                        self._port,
                        ex,
                    )
                    self._unavailable_logged = True
                raise OptomaConnectionError(
                    f"Failed to connect to {self._host}:{self._port}"
                ) from ex

    async def disconnect(self) -> None:
        """Close connection to the projector."""
        async with self._lock:
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
                self._monitor_task = None

            if self._reconnect_task:
                self._reconnect_task.cancel()
                try:
                    await self._reconnect_task
                except asyncio.CancelledError:
                    pass
                self._reconnect_task = None

            if self._writer:
                self._writer.close()
                try:
                    await self._writer.wait_closed()
                except Exception:  # noqa: S110
                    pass
                self._writer = None
                self._reader = None

            self._available = False

    async def _reconnect(self) -> None:
        """Attempt to reconnect to the projector."""
        await self.disconnect()

        # Wait before attempting reconnection
        await asyncio.sleep(5)

        try:
            await self.connect()
        except OptomaConnectionError:
            # Schedule another reconnection attempt
            if self._reconnect_task is None or self._reconnect_task.done():
                self._reconnect_task = asyncio.create_task(self._reconnect())

    async def _monitor_broadcasts(self) -> None:
        """Monitor for broadcast messages from the projector."""
        while self._reader and self._writer:
            try:
                # Read data with timeout
                data = await asyncio.wait_for(
                    self._reader.read(1024),
                    timeout=60,
                )

                if not data:
                    # Connection closed
                    _LOGGER.debug("Connection closed by projector")
                    break

                message = data.decode("ascii", errors="ignore").strip()
                _LOGGER.debug("Received broadcast: %s", message)

                # Notify listeners
                for listener in self._listeners:
                    try:
                        listener(message)
                    except Exception as ex:
                        _LOGGER.exception("Error in broadcast listener: %s", ex)

            except asyncio.TimeoutError:
                continue
            except Exception as ex:
                _LOGGER.debug("Error monitoring broadcasts: %s", ex)
                break

        # Connection lost, attempt to reconnect
        if self._available:
            _LOGGER.info("Lost connection to projector, attempting to reconnect")
            if self._reconnect_task is None or self._reconnect_task.done():
                self._reconnect_task = asyncio.create_task(self._reconnect())

    def add_listener(self, listener: Callable[[str], None]) -> Callable[[], None]:
        """Add a listener for broadcast messages."""
        self._listeners.append(listener)

        def remove_listener() -> None:
            """Remove the listener."""
            self._listeners.remove(listener)

        return remove_listener

    async def _send_command(self, command: str) -> str:
        """Send a command to the projector via telnet."""
        if not self._writer or not self._reader:
            raise OptomaConnectionError("Not connected to projector")

        async with self._lock:
            try:
                # Send command
                full_command = command + COMMAND_TERMINATOR
                self._writer.write(full_command.encode("ascii"))
                await self._writer.drain()

                # Read response with timeout
                response = await asyncio.wait_for(
                    self._reader.readuntil(COMMAND_TERMINATOR.encode("ascii")),
                    timeout=TELNET_TIMEOUT,
                )

                decoded_response = response.decode("ascii", errors="ignore").strip()
                _LOGGER.debug("Command: %s, Response: %s", command, decoded_response)

                return decoded_response

            except asyncio.TimeoutError as ex:
                raise OptomaCommandError(f"Command timeout: {command}") from ex
            except (OSError, UnicodeDecodeError) as ex:
                self._available = False
                raise OptomaConnectionError(f"Communication error: {ex}") from ex

    async def get_device_info(self) -> dict[str, str]:
        """Get device information for identification."""
        await self.connect()

        info = {}

        # Get model type
        try:
            model_response = await self._send_command(CMD_GET_MODEL)
            if model_response.startswith(RESPONSE_OK):
                # Parse model type from response (e.g., "OK6" -> "Optoma UHD")
                model_code = model_response[2:]
                info["model"] = self._parse_model_type(model_code)
        except OptomaCommandError as ex:
            _LOGGER.debug("Failed to get model: %s", ex)

        # Get serial number
        try:
            serial_response = await self._send_command(CMD_GET_SERIAL)
            if serial_response.startswith(RESPONSE_OK):
                info["serial_number"] = serial_response[2:]
        except OptomaCommandError as ex:
            _LOGGER.debug("Failed to get serial: %s", ex)

        # Get MAC address
        try:
            mac_response = await self._send_command(CMD_GET_MAC)
            if mac_response.startswith(RESPONSE_OK):
                info["mac"] = mac_response[2:]
        except OptomaCommandError as ex:
            _LOGGER.debug("Failed to get MAC: %s", ex)

        # Get software version
        try:
            sw_response = await self._send_command(CMD_GET_SW_VERSION)
            if sw_response.startswith(RESPONSE_OK):
                info["sw_version"] = sw_response[2:]
        except OptomaCommandError as ex:
            _LOGGER.debug("Failed to get software version: %s", ex)

        return info

    def _parse_model_type(self, model_code: str) -> str:
        """Parse model type code to readable name."""
        model_map = {
            "1": "Optoma SVGA",
            "2": "Optoma XGA",
            "3": "Optoma WXGA",
            "4": "Optoma 1080P",
            "5": "Optoma WUXGA",
            "6": "Optoma UHD",
        }
        return model_map.get(model_code, f"Optoma {model_code}")

    async def get_unique_id(self) -> str:
        """Get unique identifier for the projector."""
        info = await self.get_device_info()

        model = info.get("model", "Unknown")
        serial = info.get("serial_number", "Unknown")

        return f"{model}-{serial}"

    async def get_power_state(self) -> str:
        """Get power state using PJLink."""
        try:
            with PJLinkProjector.from_address(self._host, PJLINK_PORT) as projector:
                if self._password:
                    projector.authenticate(self._password)
                power_state = projector.get_power()
                return power_state
        except (ProjectorError, TimeoutError, OSError) as ex:
            raise OptomaConnectionError(f"Failed to get power state: {ex}") from ex

    async def set_power(self, state: str) -> None:
        """Set power state using PJLink."""
        try:
            with PJLinkProjector.from_address(self._host, PJLINK_PORT) as projector:
                if self._password:
                    projector.authenticate(self._password)
                projector.set_power(state)
        except (ProjectorError, TimeoutError, OSError) as ex:
            raise OptomaConnectionError(f"Failed to set power state: {ex}") from ex

    async def turn_on(self) -> None:
        """Turn the projector on."""
        await self.set_power("on")

    async def turn_off(self) -> None:
        """Turn the projector off."""
        await self.set_power("off")

    async def get_input_source(self) -> str | None:
        """Get current input source."""
        await self.connect()

        response = await self._send_command(CMD_GET_INPUT)

        # Parse response (e.g., "OK1", "OK01", "OK15", etc.)
        for code, source in INPUT_SOURCE_MAP.items():
            if response == code:
                return source

        return None

    async def set_input_source(self, source: str) -> None:
        """Set input source."""
        await self.connect()

        command_map = {
            "hdmi1": CMD_SET_INPUT_HDMI1,
            "hdmi2": CMD_SET_INPUT_HDMI2,
            "vga": CMD_SET_INPUT_VGA,
        }

        command = command_map.get(source)
        if not command:
            raise OptomaCommandError(f"Invalid input source: {source}")

        response = await self._send_command(command)

        if response == RESPONSE_FAIL:
            raise OptomaCommandError(f"Failed to set input to {source}")

    async def get_display_mode(self) -> str | None:
        """Get current display mode."""
        await self.connect()

        response = await self._send_command(CMD_GET_DISPLAY_MODE)

        # Parse response
        for code, mode in DISPLAY_MODE_MAP.items():
            if response == code:
                return mode

        return None

    async def set_display_mode(self, mode: str) -> None:
        """Set display mode."""
        await self.connect()

        command_map = {
            "cinema": CMD_SET_DISPLAY_CINEMA,
            "bright": CMD_SET_DISPLAY_BRIGHT,
            "film": CMD_SET_DISPLAY_FILM,
            "vivid": CMD_SET_DISPLAY_VIVID,
            "user": CMD_SET_DISPLAY_USER,
            "hdr": CMD_SET_DISPLAY_HDR,
        }

        command = command_map.get(mode)
        if not command:
            raise OptomaCommandError(f"Invalid display mode: {mode}")

        response = await self._send_command(command)

        if response == RESPONSE_FAIL:
            raise OptomaCommandError(f"Failed to set display mode to {mode}")

    async def set_lamp_mode(self, mode: str) -> None:
        """Set lamp mode."""
        await self.connect()

        command_map = {
            "eco": CMD_SET_LAMP_ECO,
            "bright": CMD_SET_LAMP_BRIGHT,
            "dynamic": CMD_SET_LAMP_DYNAMIC,
        }

        command = command_map.get(mode)
        if not command:
            raise OptomaCommandError(f"Invalid lamp mode: {mode}")

        response = await self._send_command(command)

        if response == RESPONSE_FAIL:
            raise OptomaCommandError(f"Failed to set lamp mode to {mode}")

    async def get_lamp_hours(self) -> int | None:
        """Get lamp hours."""
        await self.connect()

        response = await self._send_command(CMD_GET_LAMP_HOURS)

        if response.startswith(RESPONSE_OK):
            try:
                return int(response[2:])
            except ValueError:
                _LOGGER.debug("Failed to parse lamp hours: %s", response)

        return None

    async def get_brightness(self) -> int | None:
        """Get brightness value."""
        await self.connect()

        response = await self._send_command(CMD_GET_BRIGHTNESS)

        if response.startswith(RESPONSE_OK):
            try:
                return int(response[2:])
            except ValueError:
                _LOGGER.debug("Failed to parse brightness: %s", response)

        return None

    async def set_brightness(self, value: int) -> None:
        """Set brightness value."""
        await self.connect()

        command = CMD_SET_BRIGHTNESS.format(value=value)
        response = await self._send_command(command)

        if response == RESPONSE_FAIL:
            raise OptomaCommandError(f"Failed to set brightness to {value}")

    async def get_contrast(self) -> int | None:
        """Get contrast value."""
        await self.connect()

        response = await self._send_command(CMD_GET_CONTRAST)

        if response.startswith(RESPONSE_OK):
            try:
                return int(response[2:])
            except ValueError:
                _LOGGER.debug("Failed to parse contrast: %s", response)

        return None

    async def set_contrast(self, value: int) -> None:
        """Set contrast value."""
        await self.connect()

        command = CMD_SET_CONTRAST.format(value=value)
        response = await self._send_command(command)

        if response == RESPONSE_FAIL:
            raise OptomaCommandError(f"Failed to set contrast to {value}")

    async def set_brilliant_color(self, value: int) -> None:
        """Set BrilliantColor value (1-10)."""
        await self.connect()

        command = CMD_SET_BRILLIANT_COLOR.format(value=value)
        response = await self._send_command(command)

        if response == RESPONSE_FAIL:
            raise OptomaCommandError(f"Failed to set brilliant color to {value}")

    async def resync_hdmi(self) -> None:
        """Resync HDMI connection."""
        await self.connect()

        response = await self._send_command(CMD_RESYNC_HDMI)

        if response == RESPONSE_FAIL:
            raise OptomaCommandError("Failed to resync HDMI")

    async def send_navigation_command(self, command: str) -> None:
        """Send navigation command."""
        await self.connect()

        command_map = {
            "up": CMD_NAV_UP,
            "down": CMD_NAV_DOWN,
            "left": CMD_NAV_LEFT,
            "right": CMD_NAV_RIGHT,
            "select": CMD_NAV_SELECT,
            "menu": CMD_NAV_MENU,
            "info": CMD_NAV_INFO,
        }

        cmd = command_map.get(command)
        if not cmd:
            raise OptomaCommandError(f"Invalid navigation command: {command}")

        response = await self._send_command(cmd)

        if response == RESPONSE_FAIL:
            raise OptomaCommandError(f"Failed to send navigation command: {command}")
