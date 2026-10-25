"""Options flow, Edit a Device: Button layout (edisio-zmz.3)."""
import pytest
from homeassistant import data_entry_flow
from homeassistant.helpers import entity_registry as er

pytestmark = pytest.mark.asyncio

FORM = data_entry_flow.FlowResultType.FORM
THREE = "06708E57"  # stored layout: 3 Buttons -> 02 07 08
FIVE = "0670A248"  # stored layout: 5 Buttons -> 01 03 05 07 08


@pytest.fixture
def entry(add_config_entry):
    return add_config_entry(
        data={"serial_port": "/dev/ttyUSB0"},
        options={"devices": {THREE: {"active_buttons": 3}, FIVE: {"active_buttons": 5}}},
    )


async def _pick(hass, entry, radio_id):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_device"}
    )
    return await hass.config_entries.options.async_configure(result["flow_id"], {"radio_id": radio_id})


async def _edit(hass, entry, radio_id, user_input):
    form = await _pick(hass, entry, radio_id)
    assert form["type"] == FORM and form["step_id"] == "edit_device_settings"
    return await hass.config_entries.options.async_configure(form["flow_id"], user_input)


def _entity_ids(hass):
    return {e.unique_id: e.entity_id for e in er.async_get(hass).entities.values()}


async def test_layout_5_to_3_removes_dropped_buttons_and_keeps_shared(hass, entry, set_up_sensor_platform):
    await set_up_sensor_platform(entry)
    before = _entity_ids(hass)
    result = await _edit(hass, entry, FIVE, {"active_buttons": 3})
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.options["devices"][FIVE]["active_buttons"] == 3
    after = _entity_ids(hass)
    for number in ("01", "03", "05"):
        assert f"{FIVE}_button_{number}" not in after
    for number in ("07", "08"):
        assert after[f"{FIVE}_button_{number}"] == before[f"{FIVE}_button_{number}"]
    assert f"{FIVE}_battery" in after
    # the other Device is untouched
    assert {u: e for u, e in after.items() if u.startswith(THREE)} == {
        u: e for u, e in before.items() if u.startswith(THREE)
    }


async def test_new_button_numbers_are_left_to_the_reload(hass, entry, set_up_sensor_platform):
    await set_up_sensor_platform(entry)
    await _edit(hass, entry, FIVE, {"active_buttons": 3})
    assert f"{FIVE}_button_02" not in _entity_ids(hass)


async def test_form_defaults_to_stored_layout(hass, entry):
    form = await _pick(hass, entry, THREE)
    key = next(k for k in form["data_schema"].schema if k == "active_buttons")
    assert key.default() == 3


async def test_unchanged_layout_keeps_all_entities(hass, entry, set_up_sensor_platform):
    await set_up_sensor_platform(entry)
    before = _entity_ids(hass)
    await _edit(hass, entry, THREE, {"name": "BP Salon"})
    assert _entity_ids(hass) == before
    assert entry.options["devices"][THREE]["active_buttons"] == 3


async def test_layout_out_of_range_is_rejected(hass, entry):
    form = await _pick(hass, entry, THREE)
    with pytest.raises(data_entry_flow.InvalidData):
        await hass.config_entries.options.async_configure(form["flow_id"], {"active_buttons": 6})
