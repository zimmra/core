"""Tests for the Optoma UHD60 media player."""

from unittest.mock import AsyncMock, patch

from homeassistant.components.media_player import (
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    MediaPlayerState,
)
from homeassistant.components.optoma_uhd60.const import DOMAIN
from homeassistant.const import CONF_HOST, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


async def test_media_player_setup(hass: HomeAssistant) -> None:
    """Test setup of the media player."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.10"},
        unique_id="test-serial",
        title="Optoma UHD60",
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.optoma_uhd60.OptomaProjector"
    ) as mock_projector_cls:
        mock_projector = mock_projector_cls.return_value
        mock_projector.get_device_info = AsyncMock(return_value={
            "model": "UHD60",
            "serial_number": "test-serial",
            "sw_version": "C015",
        })
        mock_projector.get_power_state = AsyncMock(return_value="0")  # OFF
        mock_projector.get_input_source = AsyncMock(return_value="hdmi1")
        mock_projector.connect = AsyncMock()
        mock_projector.disconnect = AsyncMock()

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("media_player.optoma_uhd60")
    assert state
    assert state.state == STATE_OFF
    assert state.attributes["friendly_name"] == "Optoma UHD60"
    assert state.attributes["source_list"] == ["hdmi1", "hdmi2", "vga"]


async def test_commands(hass: HomeAssistant) -> None:
    """Test commands."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.10"},
        unique_id="test-serial",
        title="Optoma UHD60",
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.optoma_uhd60.OptomaProjector"
    ) as mock_projector_cls:
        mock_projector = mock_projector_cls.return_value
        mock_projector.get_device_info = AsyncMock(return_value={})
        mock_projector.get_power_state = AsyncMock(return_value="0")
        mock_projector.turn_on = AsyncMock()
        mock_projector.turn_off = AsyncMock()
        mock_projector.set_input_source = AsyncMock()
        mock_projector.get_input_source = AsyncMock(return_value="hdmi1")

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Test turn on
        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            "turn_on",
            {"entity_id": "media_player.optoma_uhd60"},
            blocking=True,
        )
        mock_projector.turn_on.assert_called_once()

        # Update mock state to ON
        mock_projector.get_power_state.return_value = "1"  # ON
        
        # Trigger update
        await hass.helpers.entity_component.async_update_entity("media_player.optoma_uhd60")
        state = hass.states.get("media_player.optoma_uhd60")
        assert state.state == STATE_ON
        assert state.attributes["source"] == "hdmi1"

        # Test select source
        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            "select_source",
            {"entity_id": "media_player.optoma_uhd60", "source": "hdmi2"},
            blocking=True,
        )
        mock_projector.set_input_source.assert_called_once_with("hdmi2")

        # Test turn off
        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            "turn_off",
            {"entity_id": "media_player.optoma_uhd60"},
            blocking=True,
        )
        mock_projector.turn_off.assert_called_once()


async def test_setup_no_device_info(hass: HomeAssistant) -> None:
    """Test setup with no device info (connection error)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.10"},
        unique_id="test-serial",
        title="Optoma UHD60",
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.optoma_uhd60.OptomaProjector"
    ) as mock_projector_cls:
        mock_projector = mock_projector_cls.return_value
        # Simulate exception
        mock_projector.get_device_info = AsyncMock(side_effect=Exception("Conn error"))
        mock_projector.get_power_state = AsyncMock(return_value="0")

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("media_player.optoma_uhd60")
    assert state
    assert state.state == STATE_OFF
    # Should still have correct name from entry title
    assert state.attributes["friendly_name"] == "Optoma UHD60"
