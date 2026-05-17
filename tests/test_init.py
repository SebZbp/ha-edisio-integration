import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from custom_components.edisio import async_setup_entry, DOMAIN

@pytest.mark.asyncio
async def test_async_setup_entry_connects_hub():
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    
    # Mock config_entries.async_forward_entry_setups to be an async function
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()

    entry = MagicMock(spec=ConfigEntry)
    entry.data = {"serial_port": "/dev/ttyUSB0"}
    entry.entry_id = "test_entry"

    with patch("custom_components.edisio.EdisioHub") as mock_hub_class:
        mock_hub_instance = MagicMock()
        mock_hub_instance.connect = AsyncMock()
        mock_hub_class.return_value = mock_hub_instance
        
        result = await async_setup_entry(hass, entry)
        
        assert result is True
        mock_hub_class.assert_called_once_with("/dev/ttyUSB0")
        mock_hub_instance.connect.assert_called_once()
        assert hass.data[DOMAIN]["test_entry"]["hub"] == mock_hub_instance

@pytest.mark.asyncio
async def test_async_setup_entry_fires_event():
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.bus = MagicMock()
    hass.bus.async_fire = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()

    entry = MagicMock(spec=ConfigEntry)
    entry.data = {"serial_port": "/dev/ttyUSB0"}
    entry.entry_id = "test_entry"

    with patch("custom_components.edisio.EdisioHub") as mock_hub_class:
        mock_hub_instance = MagicMock()
        mock_hub_instance.connect = AsyncMock()
        mock_hub_class.return_value = mock_hub_instance
        
        await async_setup_entry(hass, entry)
        
        # Simulate a packet callback
        mock_hub_instance.register_callback.assert_called_once()
        callback = mock_hub_instance.register_callback.call_args[0][0]
        
        # Test short press
        callback({"id": "01", "button": "02", "action": "toggle"})
        hass.bus.async_fire.assert_called_with(
            "edisio_button_event", 
            {"device_id": "01", "button": "02", "type": "short_press"}
        )
        
        # Test long press (dimming up/down usually represented by 'up' or 'down')
        callback({"id": "01", "button": "03", "action": "up"})
        hass.bus.async_fire.assert_called_with(
            "edisio_button_event", 
            {"device_id": "01", "button": "03", "type": "long_press"}
        )
