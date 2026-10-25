"""Options flow ("Configure" on the Dongle), driven through HA's flow manager."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr

from custom_components.edisio import async_setup_entry
from custom_components.edisio.const import DOMAIN

pytestmark = pytest.mark.asyncio


@pytest.fixture
def entry(add_config_entry):
    return add_config_entry(data={"serial_port": "/dev/ttyUSB0"})


async def _open_add_form(hass, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.MENU
    assert result["menu_options"] == ["add_device", "edit_device", "remove_device"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_device"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "add_device"
    return result


async def _add(hass, entry, user_input):
    result = await _open_add_form(hass, entry)
    return await hass.config_entries.options.async_configure(result["flow_id"], user_input)


async def test_add_device_stores_uppercased_id_with_layout_and_name(hass, entry):
    result = await _add(hass, entry, {
        "radio_id": " 0670a248 ", "active_buttons": 3, "name": " BP Cuisine ",
    })
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.options["devices"] == {
        "0670A248": {"active_buttons": 3, "name": "BP Cuisine"}
    }


async def test_add_device_defaults_to_layout_5_and_no_name(hass, entry):
    result = await _add(hass, entry, {"radio_id": "0670A248"})
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.options["devices"] == {"0670A248": {"active_buttons": 5}}


@pytest.mark.parametrize("bad", ["0670A24", "0670A2488", "0670G248", "", "1234567890"])
async def test_add_device_rejects_malformed_radio_id(hass, entry, bad):
    result = await _add(hass, entry, {"radio_id": bad})
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"radio_id": "invalid_radio_id"}
    assert "devices" not in entry.options


async def test_add_device_rejects_duplicate_radio_id(hass, entry):
    hass.config_entries.async_update_entry(
        entry, options={"devices": {"0670A248": {"active_buttons": 5}}}
    )
    result = await _add(hass, entry, {"radio_id": "0670a248", "active_buttons": 2})
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"radio_id": "already_configured"}
    assert entry.options["devices"] == {"0670A248": {"active_buttons": 5}}


async def test_add_device_applies_area_to_registry(hass, entry):
    area = ar.async_get(hass).async_create("Cuisine")
    await _add(hass, entry, {"radio_id": "0670A248", "area_id": area.id})
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "0670A248")})
    assert device is not None
    assert device.area_id == area.id


async def test_add_device_aborts_pending_discovery_flow(hass, entry):
    discovery = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "device", "device_id": "0670A248"},
        data={"device_id": "0670A248", "button": "05"},
    )
    assert discovery["type"] == data_entry_flow.FlowResultType.FORM
    await _add(hass, entry, {"radio_id": "0670a248"})
    assert not [
        f for f in hass.config_entries.flow.async_progress()
        if f["context"].get("device_id") == "0670A248"
    ]


async def test_manually_added_device_fires_button_event_on_first_packet():
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.bus = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.loop = MagicMock()
    hass.loop.call_soon_threadsafe = lambda func, *args: func(*args)
    entry = MagicMock(spec=config_entries.ConfigEntry)
    entry.data = {"serial_port": "/dev/ttyUSB0"}
    entry.options = {"devices": {"0670A248": {"active_buttons": 5}}}
    entry.entry_id = "dongle"

    with patch("custom_components.edisio.EdisioHub") as hub_class, \
         patch("homeassistant.helpers.device_registry.async_get"):
        hub = hub_class.return_value
        hub.connect = AsyncMock()
        await async_setup_entry(hass, entry)
        callback = hub.register_callback.call_args[0][0]
        callback({"id": "0670A248", "button": "05", "action": "toggle"})

    hass.bus.async_fire.assert_called_with(
        "edisio_button_event",
        {"device_id": "0670A248", "button": "05", "type": "short_press"},
    )
