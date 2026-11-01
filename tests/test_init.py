import termios

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.loader import Integration
import custom_components
from custom_components.edisio import async_setup_entry, DOMAIN

PACKET = b"\x6c\x76\x63\x00\x00\x00\x01\x01\x01\x2e\x00\x00\x03\x64\x0d\x0a"

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


@pytest.fixture
def integration(hass):
    """The real Edisio integration, as HA's loader resolves it; platforms stay unforwarded."""
    with patch.object(hass.config_entries, "async_forward_entry_setups", AsyncMock()):
        yield Integration.resolve_from_root(hass, custom_components, DOMAIN)


async def _run_setup(hass, entry, integration):
    async with entry.setup_lock:
        await entry.async_setup(hass, integration=integration)


@pytest.mark.asyncio
async def test_setup_is_retried_when_the_dongle_is_missing(hass, add_config_entry, integration, dongle):
    dongle.plugged_in = False
    entry = add_config_entry(data={"serial_port": "/dev/ttyUSB0"})

    await _run_setup(hass, entry, integration)

    assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.asyncio
async def test_failed_setup_leaves_nothing_behind(hass, add_config_entry, integration, dongle):
    dongle.plugged_in = False
    entry = add_config_entry(data={"serial_port": "/dev/ttyUSB0"})

    await _run_setup(hass, entry, integration)

    assert entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_a_half_enumerated_dongle_is_retried_too(hass, add_config_entry, integration, dongle):
    entry = add_config_entry(data={"serial_port": "/dev/ttyUSB0"})

    with patch("serial_asyncio_fast.create_serial_connection", side_effect=termios.error(5, "I/O error")):
        await _run_setup(hass, entry, integration)

    assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.asyncio
async def test_presses_reach_automations_once_a_retried_setup_finds_the_dongle(
    hass, add_config_entry, integration, dongle
):
    dongle.plugged_in = False
    entry = add_config_entry(
        data={"serial_port": "/dev/ttyUSB0"}, options={"devices": {"00000001": {"active_buttons": 8}}}
    )
    await _run_setup(hass, entry, integration)

    dongle.replug()
    await _run_setup(hass, entry, integration)
    events = []
    hass.bus.async_listen("edisio_button_event", lambda event: events.append(event.data))
    dongle.protocol.data_received(PACKET)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert events == [{"device_id": "00000001", "button": "01", "type": "short_press"}]
    await hass.data[DOMAIN][entry.entry_id]["hub"].disconnect()


@pytest.mark.asyncio
async def test_an_entry_waiting_for_the_dongle_can_be_unloaded(hass, add_config_entry, integration, dongle):
    dongle.plugged_in = False
    entry = add_config_entry(data={"serial_port": "/dev/ttyUSB0"})
    await _run_setup(hass, entry, integration)

    async with entry.setup_lock:
        assert await entry.async_unload(hass, integration=integration) is True

    assert entry.state is ConfigEntryState.NOT_LOADED
