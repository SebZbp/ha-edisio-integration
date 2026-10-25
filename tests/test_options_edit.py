"""Options flow, Edit a Device: name, entity IDs and area (edisio-zmz.2)."""
import pytest
from homeassistant import data_entry_flow
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.edisio.const import DOMAIN

pytestmark = pytest.mark.asyncio

RADIO_ID = "06708E57"
FORM = data_entry_flow.FlowResultType.FORM


@pytest.fixture
def entry(add_config_entry):
    return add_config_entry(
        data={"serial_port": "/dev/ttyUSB0"},
        options={"devices": {
            RADIO_ID: {"active_buttons": 3, "name": "BP Cuisine"},
            "0670A248": {"active_buttons": 5},
        }},
    )


async def _pick(hass, entry, radio_id=RADIO_ID):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_device"}
    )
    assert result["type"] == FORM and result["step_id"] == "edit_device"
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {"radio_id": radio_id}
    )


async def _edit(hass, entry, user_input, radio_id=RADIO_ID):
    form = await _pick(hass, entry, radio_id)
    assert form["type"] == FORM and form["step_id"] == "edit_device_settings"
    return await hass.config_entries.options.async_configure(form["flow_id"], user_input)


def _device(hass, radio_id=RADIO_ID):
    return dr.async_get(hass).async_get_device(identifiers={(DOMAIN, radio_id)})


def _entity_ids(hass):
    return {e.unique_id: e.entity_id for e in er.async_get(hass).entities.values()}


async def test_pick_step_lists_devices_by_name_and_radio_id(hass, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_device"}
    )
    options = result["data_schema"].schema["radio_id"].config["options"]
    assert {o["value"]: o["label"] for o in options} == {
        RADIO_ID: "BP Cuisine (06708E57)",
        "0670A248": "Edisio EBP8-B 0670A248 (0670A248)",
    }


async def test_rename_stores_name_and_clears_name_by_user(hass, entry, set_up_sensor_platform):
    await set_up_sensor_platform(entry)
    dr.async_get(hass).async_update_device(_device(hass).id, name_by_user="Renamed in UI")
    result = await _edit(hass, entry, {"name": " BP Salon "})
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.options["devices"][RADIO_ID] == {"active_buttons": 3, "name": "BP Salon"}
    device = _device(hass)
    assert device.name_by_user is None
    assert device.name == "BP Salon"


async def test_empty_name_removes_stored_name(hass, entry):
    await _edit(hass, entry, {"name": ""})
    assert entry.options["devices"][RADIO_ID] == {"active_buttons": 3}


async def test_edit_form_is_prefilled_with_name_and_registry_area(hass, entry, set_up_sensor_platform):
    await set_up_sensor_platform(entry)
    area = ar.async_get(hass).async_create("Cuisine")
    dr.async_get(hass).async_update_device(_device(hass).id, area_id=area.id)
    form = await _pick(hass, entry)
    suggested = {
        str(k): k.description["suggested_value"]
        for k in form["data_schema"].schema
        if k.description and "suggested_value" in k.description
    }
    assert suggested == {"name": "BP Cuisine", "area_id": area.id}


async def test_area_change_lands_in_device_registry(hass, entry, set_up_sensor_platform):
    await set_up_sensor_platform(entry)
    area = ar.async_get(hass).async_create("Salon")
    await _edit(hass, entry, {"name": "BP Cuisine", "area_id": area.id})
    assert _device(hass).area_id == area.id


async def test_clearing_area_removes_it(hass, entry, set_up_sensor_platform):
    await set_up_sensor_platform(entry)
    area = ar.async_get(hass).async_create("Salon")
    dr.async_get(hass).async_update_device(_device(hass).id, area_id=area.id)
    await _edit(hass, entry, {"name": "BP Cuisine"})
    assert _device(hass).area_id is None


async def test_entity_ids_untouched_by_default(hass, entry, set_up_sensor_platform):
    await set_up_sensor_platform(entry)
    before = _entity_ids(hass)
    await _edit(hass, entry, {"name": "BP Salon"})
    assert _entity_ids(hass) == before


async def test_checkbox_rewrites_entity_ids_and_keeps_unique_ids(hass, entry, set_up_sensor_platform):
    await set_up_sensor_platform(entry)
    unique_ids = set(_entity_ids(hass))
    result = await _edit(hass, entry, {"name": "BP Salon", "update_entity_ids": True})
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    ids = _entity_ids(hass)
    assert set(ids) == unique_ids
    assert ids[f"{RADIO_ID}_battery"] == "sensor.bp_salon_battery"
    assert ids[f"{RADIO_ID}_button_02"] == "sensor.bp_salon_button_02"
    assert ids[f"{RADIO_ID}_button_07"] == "sensor.bp_salon_button_07"
    assert ids[f"{RADIO_ID}_button_08"] == "sensor.bp_salon_button_08"
    assert ids["0670A248_battery"] != "sensor.bp_salon_battery"


async def test_taken_entity_id_is_skipped_and_reported(hass, entry, set_up_sensor_platform):
    await set_up_sensor_platform(entry)
    reg = er.async_get(hass)
    reg.async_get_or_create("sensor", "other", "other-1", suggested_object_id="bp_salon_battery")
    result = await _edit(hass, entry, {"name": "BP Salon", "update_entity_ids": True})
    ids = _entity_ids(hass)
    assert ids["other-1"] == "sensor.bp_salon_battery"
    assert ids[f"{RADIO_ID}_battery"] != "sensor.bp_salon_battery"
    assert ids[f"{RADIO_ID}_button_02"] == "sensor.bp_salon_button_02"
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "entity_ids_skipped"
    assert "sensor.bp_salon_battery" in result["description_placeholders"]["skipped"]
    assert entry.options["devices"][RADIO_ID]["name"] == "BP Salon"
