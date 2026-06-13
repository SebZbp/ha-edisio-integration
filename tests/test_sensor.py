import pytest
import asyncio
from unittest.mock import MagicMock, patch
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.core import callback
from custom_components.edisio.sensor import async_setup_entry, EdisioBatterySensor, EdisioButtonSensor
from custom_components.edisio.const import DOMAIN

@pytest.mark.asyncio
@patch("custom_components.edisio.sensor.async_dispatcher_connect")
async def test_sensor_creation_and_update(mock_dispatcher_connect):
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    config_entry.options = {}
    hass.data = {DOMAIN: {"test_entry": {"devices": set()}}}
    
    async_add_entities = MagicMock()
    
    # Setup the sensor platform
    await async_setup_entry(hass, config_entry, async_add_entities)
    
    # Simulate async_dispatcher_connect callback firing for discover
    discover_callback = None
    for call in mock_dispatcher_connect.call_args_list:
        if call[0][1] == f"{DOMAIN}_discover":
            discover_callback = call[0][2]
            break
            
    assert discover_callback is not None
    
    # Fire discover callback for a device with active_buttons option default (5 buttons)
    discover_callback({"id": "01", "battery": "100"})
    
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    
    # Should create 1 battery sensor + 5 button sensors
    assert len(entities) == 6
    assert isinstance(entities[0], EdisioBatterySensor)
    assert entities[0].unique_id == "01_battery"
    
    button_sensors = [e for e in entities if isinstance(e, EdisioButtonSensor)]
    assert len(button_sensors) == 5
    assert button_sensors[0].unique_id == "01_button_01"
    assert button_sensors[0].name == "Button 1"
    assert button_sensors[4].unique_id == "01_button_08"
    assert button_sensors[4].name == "Button 5"

    # Test battery update
    battery_sensor = entities[0]
    battery_sensor.hass = hass
    battery_sensor.async_write_ha_state = MagicMock()
    
    # Manually call _update_battery like the dispatcher would
    battery_sensor._update_battery({"id": "01", "battery": "85"})
    
    assert battery_sensor.native_value == 85
    battery_sensor.async_write_ha_state.assert_called_once()

@pytest.mark.asyncio
async def test_sensor_setup_from_options():
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    config_entry.options = {"devices": {"device_abc": {"active_buttons": 2}}}
    hass.data = {DOMAIN: {"test_entry": {"devices": set()}}}
    
    async_add_entities = MagicMock()
    await async_setup_entry(hass, config_entry, async_add_entities)
    
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    
    # Should create 1 battery sensor + 2 button sensors for config option 2 (buttons 04 and 06)
    assert len(entities) == 3
    assert entities[0].unique_id == "device_abc_battery"
    assert entities[1].unique_id == "device_abc_button_04"
    assert entities[1].name == "Button 1"
    assert entities[2].unique_id == "device_abc_button_06"
    assert entities[2].name == "Button 2"

@pytest.mark.asyncio
async def test_button_sensor_press_and_reset():
    hass = MagicMock()
    created_tasks = []
    
    def mock_async_create_task(coro):
        task = asyncio.create_task(coro)
        created_tasks.append(task)
        return task
        
    hass.async_create_task = mock_async_create_task
    
    button_sensor = EdisioButtonSensor("device_123", "05", 3, "test_entry")
    button_sensor.hass = hass
    button_sensor.async_write_ha_state = MagicMock()
    
    # Check initial state
    assert button_sensor.native_value == "normal"
    assert button_sensor.name == "Button 3"
    
    # 1. Test short press update (non-long press action)
    button_sensor._update_button({"id": "device_123", "button": "05", "action": "toggle"})
    assert button_sensor.native_value == "short-press"
    button_sensor.async_write_ha_state.assert_called_once()
    assert button_sensor._reset_task is not None
    
    # 2. Test long press update (long press actions like 'up' or 'down')
    button_sensor.async_write_ha_state.reset_mock()
    button_sensor._update_button({"id": "device_123", "button": "05", "action": "up"})
    assert button_sensor.native_value == "long-press"
    button_sensor.async_write_ha_state.assert_called_once()
    
    # Wait for the auto-reset task to finish
    await asyncio.sleep(1.1)
    
    assert button_sensor.native_value == "normal"
    assert button_sensor._reset_task is None
    
    # Clean up tasks
    for task in created_tasks:
        if not task.done():
            task.cancel()
