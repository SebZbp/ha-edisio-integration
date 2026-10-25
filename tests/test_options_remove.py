"""Options flow, Remove a Device branch (edisio-zmz.4), driven through HA's flow manager."""
import pytest
from unittest.mock import AsyncMock, patch
from homeassistant import data_entry_flow
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.edisio import async_setup_entry
from custom_components.edisio.const import DOMAIN

pytestmark = pytest.mark.asyncio

DEVICES = {
    "06708E57": {"active_buttons": 5, "name": "BP Cuisine"},
    "0670A248": {"active_buttons": 3},
}


@pytest.fixture
def entry(add_config_entry):
    return add_config_entry(data={"serial_port": "/dev/ttyUSB0"}, options={"devices": dict(DEVICES)})


def _register(hass, entry, radio_id):
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, radio_id)}, name=radio_id
    )
    for suffix in ("battery", "button_05"):
        er.async_get(hass).async_get_or_create(
            "sensor", DOMAIN, f"{radio_id}_{suffix}", config_entry=entry, device_id=device.id
        )


async def _open_remove_form(hass, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_device"}
    )


async def test_remove_form_lists_devices_by_name_and_radio_id(hass, entry):
    result = await _open_remove_form(hass, entry)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "remove_device"
    selector = result["data_schema"].schema["radio_id"]
    options = {o["value"]: o["label"] for o in selector.config["options"]}
    assert options == {
        "06708E57": "BP Cuisine (06708E57)",
        "0670A248": "Edisio EBP8-B 0670A248 (0670A248)",
    }


async def test_remove_device_deletes_options_device_and_entities(hass, entry):
    _register(hass, entry, "06708E57")
    _register(hass, entry, "0670A248")
    result = await _open_remove_form(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"radio_id": "06708E57"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.options["devices"] == {"0670A248": DEVICES["0670A248"]}
    assert dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "06708E57")}) is None
    entities = er.async_get(hass)
    assert entities.async_get_entity_id("sensor", DOMAIN, "06708E57_battery") is None
    assert entities.async_get_entity_id("sensor", DOMAIN, "06708E57_button_05") is None
    # The other Device is untouched.
    assert dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "0670A248")}) is not None
    assert entities.async_get_entity_id("sensor", DOMAIN, "0670A248_battery") is not None


async def test_remove_device_without_registry_entries(hass, entry):
    result = await _open_remove_form(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"radio_id": "0670A248"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert list(entry.options["devices"]) == ["06708E57"]


async def test_remove_with_no_configured_device_aborts(hass, add_config_entry):
    entry = add_config_entry(data={"serial_port": "/dev/ttyUSB0"})
    result = await _open_remove_form(hass, entry)
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "no_devices"


async def test_packet_from_removed_device_starts_discovery_flow(hass, entry):
    with patch("custom_components.edisio.EdisioHub") as hub_class, \
         patch.object(hass.config_entries, "async_forward_entry_setups", AsyncMock()), \
         patch.object(hass.config_entries, "async_reload", AsyncMock()):
        hub = hub_class.return_value
        hub.connect = AsyncMock()
        await async_setup_entry(hass, entry)
        packet = hub.register_callback.call_args[0][0]

        result = await _open_remove_form(hass, entry)
        await hass.config_entries.options.async_configure(
            result["flow_id"], {"radio_id": "06708E57"}
        )
        packet({"id": "06708E57", "button": "05", "action": "toggle"})
        await hass.async_block_till_done()

    flows = [
        f for f in hass.config_entries.flow.async_progress()
        if f["context"].get("device_id") == "06708E57"
    ]
    assert len(flows) == 1
