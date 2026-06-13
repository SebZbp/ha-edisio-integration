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

    with patch("custom_components.edisio.EdisioHub") as mock_hub_class, \
         patch("homeassistant.helpers.device_registry.async_get") as mock_async_get:
        mock_dr = MagicMock()
        mock_async_get.return_value = mock_dr
        mock_hub_instance = MagicMock()
        mock_hub_instance.connect = AsyncMock()
        mock_hub_class.return_value = mock_hub_instance
        
        result = await async_setup_entry(hass, entry)
        
        assert result is True
        mock_hub_class.assert_called_once_with("/dev/ttyUSB0")
        mock_hub_instance.connect.assert_called_once()
        assert hass.data[DOMAIN]["test_entry"]["hub"] == mock_hub_instance
        mock_async_get.assert_called_once_with(hass)
        mock_dr.async_get_or_create.assert_called_once()

@pytest.mark.asyncio
async def test_async_setup_entry_fires_event():
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.bus = MagicMock()
    hass.bus.async_fire = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.loop = MagicMock()
    hass.loop.call_soon_threadsafe = lambda func, *args: func(*args)

    entry = MagicMock(spec=ConfigEntry)
    entry.data = {"serial_port": "/dev/ttyUSB0"}
    entry.options = {"devices": {"01": {"active_buttons": 5}}}
    entry.entry_id = "test_entry"

    with patch("custom_components.edisio.EdisioHub") as mock_hub_class, \
         patch("homeassistant.helpers.device_registry.async_get") as mock_async_get:
        mock_dr = MagicMock()
        mock_async_get.return_value = mock_dr
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

@pytest.mark.asyncio
async def test_init_triggers_discovery_for_unconfigured_device():
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.bus = MagicMock()
    hass.bus.async_fire = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.flow = MagicMock()
    hass.config_entries.flow.async_progress = MagicMock(return_value=[])
    hass.config_entries.flow.async_init = MagicMock()
    hass.loop = MagicMock()
    hass.loop.call_soon_threadsafe = lambda func, *args: func(*args)

    entry = MagicMock(spec=ConfigEntry)
    entry.data = {"serial_port": "/dev/ttyUSB0"}
    entry.options = {}
    entry.entry_id = "test_entry"

    with patch("custom_components.edisio.EdisioHub") as mock_hub_class, \
         patch("homeassistant.helpers.device_registry.async_get") as mock_async_get:
        mock_dr = MagicMock()
        mock_async_get.return_value = mock_dr
        mock_hub_instance = MagicMock()
        mock_hub_instance.connect = AsyncMock()
        mock_hub_class.return_value = mock_hub_instance
        
        await async_setup_entry(hass, entry)
        
        # Simulate a packet callback
        callback = mock_hub_instance.register_callback.call_args[0][0]
        
        # Trigger event for unconfigured device "02"
        callback({"id": "02", "button": "01", "action": "toggle"})
        
        # Verify no event was fired
        hass.bus.async_fire.assert_not_called()
        
        # Verify config flow was initiated
        hass.config_entries.flow.async_init.assert_called_once_with(
            DOMAIN,
            context={"source": "device", "device_id": "02"},
            data={"device_id": "02"}
        )
