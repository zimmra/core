"""The Optoma UHD60 integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from .projector import OptomaProjector

_PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]

type OptomaConfigEntry = ConfigEntry[OptomaProjector]


async def async_setup_entry(hass: HomeAssistant, entry: OptomaConfigEntry) -> bool:
    """Set up Optoma UHD60 from a config entry."""

    host = entry.data[CONF_HOST]
    projector = OptomaProjector(host)
    # We do not connect here as we want to do it when the entity is added
    # or let the entity handle the connection logic to avoid startup blocking
    # However, for this implementation, let's keep it simple and just store it.
    # The projector client handles connection internally in its methods or via connect()

    entry.runtime_data = projector

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: OptomaConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, _PLATFORMS):
        await entry.runtime_data.disconnect()

    return unload_ok
