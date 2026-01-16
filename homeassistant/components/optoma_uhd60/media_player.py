"""Media Player entity for Optoma UHD60 Projector."""

from __future__ import annotations

import logging

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OptomaConfigEntry
from .const import DOMAIN, INPUT_SOURCE_MAP
from .projector import OptomaConnectionError, OptomaProjector

_LOGGER = logging.getLogger(__name__)

# Map PJLink states to MediaPlayerState
PJLINK_STATE_OFF = "0"
PJLINK_STATE_ON = "1"
PJLINK_STATE_COOLING = "2"
PJLINK_STATE_WARMUP = "3"

PJLINK_STATE_MAP = {
    PJLINK_STATE_OFF: MediaPlayerState.OFF,
    PJLINK_STATE_ON: MediaPlayerState.ON,
    PJLINK_STATE_COOLING: MediaPlayerState.OFF,  # Or logic to show cooling
    PJLINK_STATE_WARMUP: MediaPlayerState.ON,    # Or logic to show warming
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OptomaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Optoma UHD60 media player."""
    projector = entry.runtime_data
    unique_id = entry.unique_id
    assert unique_id is not None

    # Fetch initial device info if possible, but don't block too long
    # The projector client might need connection for get_device_info
    # We will rely on async_update to populate dynamic data
    
    try:
        device_info = await projector.get_device_info()
    except Exception:
        device_info = {}
    
    async_add_entities(
        [OptomaUHD60MediaPlayer(projector, unique_id, device_info, entry.title)]
    )


class OptomaUHD60MediaPlayer(MediaPlayerEntity):
    """Representation of an Optoma UHD60 Projector."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = True
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    def __init__(
        self,
        projector: OptomaProjector,
        unique_id: str,
        device_info: dict[str, str],
        entry_title: str,
    ) -> None:
        """Initialize the media player."""
        self._projector = projector
        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            manufacturer="Optoma",
            model=device_info.get("model", "UHD60"),
            name=entry_title,
            sw_version=device_info.get("sw_version"),
            serial_number=device_info.get("serial_number"),
        )
        self._attr_source_list = sorted(list(set(INPUT_SOURCE_MAP.values())))

    async def async_update(self) -> None:
        """Update the state of the projector."""
        try:
            # Update Power State
            power_state = await self._projector.get_power_state()
            self._attr_state = PJLINK_STATE_MAP.get(power_state, MediaPlayerState.OFF)
            self._attr_available = True
        except OptomaConnectionError:
            self._attr_available = False
            _LOGGER.debug("Projector unavailable (PJLink)")
            return
        except Exception as ex:
            _LOGGER.error("Error updating projector power status: %s", ex)
            self._attr_available = False
            return

        # Update Source if On
        if self._attr_state == MediaPlayerState.ON:
            try:
                self._attr_source = await self._projector.get_input_source()
            except OptomaConnectionError:
                _LOGGER.debug("Unable to retrieve input source (Telnet)")
                self._attr_source = None
        else:
            self._attr_source = None

    async def async_turn_on(self) -> None:
        """Turn the projector on."""
        try:
            await self._projector.turn_on()
            self._attr_state = MediaPlayerState.ON
        except OptomaConnectionError as ex:
            _LOGGER.error("Failed to turn on projector: %s", ex)
            self._attr_available = False

    async def async_turn_off(self) -> None:
        """Turn the projector off."""
        try:
            await self._projector.turn_off()
            self._attr_state = MediaPlayerState.OFF
        except OptomaConnectionError as ex:
            _LOGGER.error("Failed to turn off projector: %s", ex)
            self._attr_available = False

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        try:
            await self._projector.set_input_source(source)
            self._attr_source = source
        except OptomaConnectionError as ex:
            _LOGGER.error("Failed to select source %s: %s", source, ex)
            self._attr_available = False
