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
        
        # Verify config flow was initiated via async_create_task
        hass.async_create_task.assert_called_once()
        hass.config_entries.flow.async_init.assert_called_once_with(
            DOMAIN,
            context={"source": "device", "device_id": "02"},
            data={"device_id": "02", "button": "01"}
        )


@pytest.mark.asyncio
async def test_init_second_press_while_flow_in_progress_starts_no_flow():
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.bus = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.flow = MagicMock()
    hass.config_entries.flow.async_progress = MagicMock(return_value=[
        {"handler": DOMAIN, "context": {"device_id": "02"}}
    ])
    hass.config_entries.flow.async_init = MagicMock()
    hass.loop = MagicMock()
    hass.loop.call_soon_threadsafe = lambda func, *args: func(*args)

    entry = MagicMock(spec=ConfigEntry)
    entry.data = {"serial_port": "/dev/ttyUSB0"}
    entry.options = {}
    entry.entry_id = "test_entry"

    with patch("custom_components.edisio.EdisioHub") as mock_hub_class, \
         patch("homeassistant.helpers.device_registry.async_get"):
        mock_hub_instance = MagicMock()
        mock_hub_instance.connect = AsyncMock()
        mock_hub_class.return_value = mock_hub_instance

        await async_setup_entry(hass, entry)
        callback = mock_hub_instance.register_callback.call_args[0][0]
        callback({"id": "02", "button": "03", "action": "toggle"})

        hass.config_entries.flow.async_init.assert_not_called()


@pytest.mark.asyncio
async def test_async_unload_entry_disconnects_hub():
    from custom_components.edisio import async_unload_entry

    hass = MagicMock(spec=HomeAssistant)
    hub = MagicMock()
    hub.disconnect = AsyncMock()
    hass.data = {DOMAIN: {"test_entry": {"hub": hub}}}
    hass.config_entries = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    assert await async_unload_entry(hass, entry) is True

    hub.disconnect.assert_awaited_once()
    assert "test_entry" not in hass.data[DOMAIN]


def _setup_unconfigured(progress=()):
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.bus = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.flow.async_progress = MagicMock(return_value=list(progress))
    hass.config_entries.flow.async_init = MagicMock()
    hass.loop = MagicMock()
    hass.loop.call_soon_threadsafe = lambda func, *args: func(*args)
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {"serial_port": "/dev/ttyUSB0"}
    entry.options = {}
    entry.entry_id = "test_entry"
    return hass, entry


async def _press(hass, entry, event):
    with patch("custom_components.edisio.EdisioHub") as mock_hub_class, \
         patch("homeassistant.helpers.device_registry.async_get"):
        hub = MagicMock()
        hub.connect = AsyncMock()
        mock_hub_class.return_value = hub
        await async_setup_entry(hass, entry)
        hub.register_callback.call_args[0][0](event)


@pytest.mark.asyncio
async def test_unconfigured_device_with_non_ebp8_button_starts_no_flow(caplog):
    hass, entry = _setup_unconfigured()
    with caplog.at_level("DEBUG", logger="custom_components.edisio"):
        await _press(hass, entry, {"id": "70051C01", "button": "00", "action": "toggle"})

    hass.config_entries.flow.async_init.assert_not_called()
    assert "Ignoring unconfigured device 70051C01" in caplog.text


@pytest.mark.asyncio
async def test_repeated_presses_while_flow_pending_are_logged(caplog):
    hass, entry = _setup_unconfigured(progress=[{"handler": DOMAIN, "context": {"device_id": "02"}}])
    with caplog.at_level("DEBUG", logger="custom_components.edisio"):
        await _press(hass, entry, {"id": "02", "button": "03", "action": "toggle"})

    hass.config_entries.flow.async_init.assert_not_called()
    assert "already in progress for 02" in caplog.text
