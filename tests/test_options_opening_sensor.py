"""Options flow for an Opening sensor: add by Radio ID, edit, rename entity IDs, remove."""
import pytest
from homeassistant import data_entry_flow
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.edisio import binary_sensor, sensor
from custom_components.edisio.const import DOMAIN

pytestmark = pytest.mark.asyncio

SENSOR = "91107A5D"
FORM = data_entry_flow.FlowResultType.FORM
CREATE = data_entry_flow.FlowResultType.CREATE_ENTRY


@pytest.fixture
def entry(add_config_entry):
    return add_config_entry(
        data={"serial_port": "/dev/ttyUSB0"},
        options={"devices": {SENSOR: {"device_model": "opening_sensor"}}},
    )


async def _step(hass, entry, step_id, user_input=None):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": step_id}
    )
    if user_input is None:
        return result
    return await hass.config_entries.options.async_configure(result["flow_id"], user_input)


async def _set_up_entities(hass, entry, set_up_platform):
    await set_up_platform(entry, sensor, "sensor")
    await set_up_platform(entry, binary_sensor, "binary_sensor")


async def test_add_sensor_by_radio_id_stores_model_without_layout(hass, entry):
    result = await _step(hass, entry, "add_device", {
        "radio_id": "0A0B0C0D", "device_model": "opening_sensor", "name": "Porte",
    })
    assert result["type"] == CREATE
    assert entry.options["devices"]["0A0B0C0D"] == {"device_model": "opening_sensor", "name": "Porte"}


async def test_add_sensor_ignores_a_submitted_layout(hass, entry):
    await _step(hass, entry, "add_device", {
        "radio_id": "0A0B0C0D", "device_model": "opening_sensor", "active_buttons": 3,
    })
    assert entry.options["devices"]["0A0B0C0D"] == {"device_model": "opening_sensor"}


async def test_add_wall_plate_by_choice_keeps_layout(hass, entry):
    await _step(hass, entry, "add_device", {
        "radio_id": "0A0B0C0D", "device_model": "wall_plate", "active_buttons": 3,
    })
    assert entry.options["devices"]["0A0B0C0D"]["active_buttons"] == 3
    assert entry.options["devices"]["0A0B0C0D"].get("device_model", "wall_plate") == "wall_plate"


async def test_add_form_offers_both_device_models(hass, entry):
    form = await _step(hass, entry, "add_device")
    selector = form["data_schema"].schema["device_model"]
    assert set(selector.config["options"]) == {"wall_plate", "opening_sensor"}


async def test_edit_form_of_a_sensor_has_no_button_layout(hass, entry):
    result = await _step(hass, entry, "edit_device")
    form = await hass.config_entries.options.async_configure(result["flow_id"], {"radio_id": SENSOR})
    assert form["step_id"] == "edit_device_settings"
    assert set(map(str, form["data_schema"].schema)) == {"name", "area_id", "update_entity_ids"}


async def test_edit_sensor_name_keeps_model_and_adds_no_layout(hass, entry, set_up_platform):
    await _set_up_entities(hass, entry, set_up_platform)
    result = await _step(hass, entry, "edit_device")
    form = await hass.config_entries.options.async_configure(result["flow_id"], {"radio_id": SENSOR})
    result = await hass.config_entries.options.async_configure(form["flow_id"], {"name": "Porte"})
    assert result["type"] == CREATE
    assert entry.options["devices"][SENSOR] == {"device_model": "opening_sensor", "name": "Porte"}


async def test_update_entity_ids_renames_binary_sensor_and_battery(hass, entry, set_up_platform):
    await _set_up_entities(hass, entry, set_up_platform)
    result = await _step(hass, entry, "edit_device")
    form = await hass.config_entries.options.async_configure(result["flow_id"], {"radio_id": SENSOR})
    await hass.config_entries.options.async_configure(
        form["flow_id"], {"name": "Porte Cave", "update_entity_ids": True}
    )
    ids = {e.unique_id: e.entity_id for e in er.async_get(hass).entities.values()}
    assert ids[f"{SENSOR}_opening"] == "binary_sensor.porte_cave_opening"
    assert ids[f"{SENSOR}_battery"] == "sensor.porte_cave_battery"


async def test_remove_sensor_deletes_its_entities(hass, entry, set_up_platform):
    await _set_up_entities(hass, entry, set_up_platform)

    def sensor_entities():
        return {e.unique_id for e in er.async_get(hass).entities.values() if e.unique_id.startswith(SENSOR)}

    assert sensor_entities() == {f"{SENSOR}_opening", f"{SENSOR}_battery"}
    result = await _step(hass, entry, "remove_device", {"radio_id": SENSOR})
    assert result["type"] == CREATE
    assert entry.options["devices"] == {}
    assert not sensor_entities()
    assert dr.async_get(hass).async_get_device(identifiers={(DOMAIN, SENSOR)}) is None
