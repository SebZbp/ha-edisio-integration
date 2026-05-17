import pytest
from unittest.mock import MagicMock
from homeassistant.helpers.dispatcher import async_dispatcher_send
from custom_components.edisio.sensor import async_setup_entry, EdisioBatterySensor
from custom_components.edisio.const import DOMAIN

from unittest.mock import MagicMock, patch

@pytest.mark.asyncio
@patch("custom_components.edisio.sensor.async_dispatcher_connect")
async def test_sensor_creation_and_update(mock_dispatcher_connect):
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    hass.data = {DOMAIN: {"test_entry": {"devices": set()}}}
    
    async_add_entities = MagicMock()
    
    # 1. Setup the sensor platform
    await async_setup_entry(hass, config_entry, async_add_entities)
    
    # Simulate async_dispatcher_connect callback firing
    discover_callback = mock_dispatcher_connect.call_args[0][2]
    
    # 2. Fire discover callback
    discover_callback({"id": "01", "battery": "100"})
    
    # Assert entity added
    async_add_entities.assert_called_once()
    sensor = async_add_entities.call_args[0][0][0]
    assert isinstance(sensor, EdisioBatterySensor)
    assert sensor.unique_id == "01_battery"
    
    # 3. Test battery update
    sensor.hass = hass
    sensor.async_write_ha_state = MagicMock()
    
    # Manually call _update_battery like the dispatcher would
    sensor._update_battery({"id": "01", "battery": "85"})
    
    assert sensor.native_value == 85
    sensor.async_write_ha_state.assert_called_once()
