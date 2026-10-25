"""The automation blueprint, checked against the Button layouts (spec: blueprint-button-numbers)."""
import re
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.automation.config import async_validate_config_item
from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.components.blueprint.schemas import BLUEPRINT_SCHEMA
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.template import Template
from homeassistant.util.yaml import load_yaml

from custom_components.edisio import async_setup_entry
from custom_components.edisio.const import BUTTON_LAYOUTS, DOMAIN

BLUEPRINT_PATH = (
    Path(__file__).parent.parent / "blueprints" / "automation" / "edisio" / "ebp8b_controller.yaml"
)

# Every Button number some Button layout can send.
BUTTON_NUMBERS = set().union(*BUTTON_LAYOUTS.values())


@pytest.fixture
def blueprint() -> Blueprint:
    return Blueprint(
        load_yaml(BLUEPRINT_PATH),
        expected_domain="automation",
        schema=BLUEPRINT_SCHEMA,
    )


def _choose_branches(blueprint: Blueprint) -> list[dict]:
    for step in blueprint.data["action"]:
        if "choose" in step:
            return step["choose"]
    raise AssertionError("blueprint has no choose step")


def test_button_layouts_cover_button_numbers_01_to_08():
    assert BUTTON_NUMBERS == {"01", "02", "03", "04", "05", "06", "07", "08"}


def test_blueprint_handles_exactly_the_button_numbers_of_all_layouts(blueprint):
    handled = set()
    for branch in _choose_branches(blueprint):
        for condition in branch["conditions"]:
            handled.update(re.findall(r"button == '(\d\d)'", condition))
    assert handled == BUTTON_NUMBERS


def test_blueprint_has_short_and_long_action_per_button_in_sections(blueprint):
    sections = {
        key: value for key, value in blueprint.data["blueprint"]["input"].items()
        if "input" in value
    }
    for number in sorted(BUTTON_NUMBERS):
        section = sections[f"button_{number}"]
        assert section["name"] == f"Button {number}"
        assert section["collapsed"] is True
        assert set(section["input"]) == {f"button_{number}_short", f"button_{number}_long"}
        for key in section["input"]:
            assert section["input"][key]["default"] == []
            assert "action" in section["input"][key]["selector"]


def test_section_descriptions_name_the_layouts_containing_the_button(blueprint):
    inputs = blueprint.data["blueprint"]["input"]
    for number in sorted(BUTTON_NUMBERS):
        description = inputs[f"button_{number}"]["description"]
        for layout, numbers in BUTTON_LAYOUTS.items():
            mentioned = f"{layout}-Button" in description
            assert mentioned == (number in numbers), (number, layout, description)


def test_every_branch_runs_its_matching_input(blueprint):
    for branch in _choose_branches(blueprint):
        (condition,) = branch["conditions"]
        number, press = re.fullmatch(
            r"\{\{ button == '(\d\d)' and press_type == '(short|long)_press' \}\}", condition
        ).groups()
        assert branch["sequence"].name == f"button_{number}_{press}"


def _matches_device_filter(hass, device: dr.DeviceEntry, filters: list[dict]) -> bool:
    """Whether the device selector offers ``device`` (HA frontend rule: any filter matches,
    a filter matching when all of its integration/manufacturer/model criteria hold)."""
    domains = {
        hass.config_entries.async_get_entry(entry_id).domain
        for entry_id in device.config_entries
    }

    def matches(criteria: dict) -> bool:
        return (
            ("integration" not in criteria or criteria["integration"] in domains)
            and ("manufacturer" not in criteria or criteria["manufacturer"] == device.manufacturer)
            and ("model" not in criteria or criteria["model"] == device.model)
        )

    return any(matches(criteria) for criteria in filters)


@pytest.mark.asyncio
async def test_device_selector_offers_devices_but_not_the_dongle(
    hass, add_config_entry, set_up_sensor_platform, blueprint
):
    entry = add_config_entry(
        data={"serial_port": "/dev/null"},
        options={"devices": {"06709603": {"active_buttons": 5}}},
    )
    # Real integration setup registers the Dongle; the sensor platform registers the Device.
    with patch("custom_components.edisio.EdisioHub") as hub_class, patch.object(
        hass.config_entries, "async_forward_entry_setups", AsyncMock()
    ):
        hub_class.return_value.connect = AsyncMock()
        assert await async_setup_entry(hass, entry)
    await set_up_sensor_platform(entry)

    registry = dr.async_get(hass)
    dongle = registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    device = registry.async_get_device(identifiers={(DOMAIN, "06709603")})
    filters = blueprint.data["blueprint"]["input"]["edisio_device"]["selector"]["device"]["filter"]

    assert not _matches_device_filter(hass, dongle, filters)
    assert _matches_device_filter(hass, device, filters)
    assert "edisio_device_id" not in blueprint.inputs


def test_requires_ha_version_with_input_sections(blueprint):
    assert blueprint.data["blueprint"]["homeassistant"]["min_version"] == "2024.6.0"
    assert blueprint.data["mode"] == "queued"


@pytest.mark.asyncio
async def test_radio_id_is_derived_from_the_selected_device(hass, add_config_entry, blueprint):
    entry = add_config_entry()
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "06709603")},
        name="BP Bas escalier",
    )
    radio_id = Template(blueprint.data["variables"]["radio_id"], hass).async_render(
        {"edisio_device": device.id}
    )
    assert radio_id == "06709603"


@pytest.mark.asyncio
async def test_automation_from_blueprint_passes_ha_validation(hass, blueprint):
    inputs = BlueprintInputs(
        blueprint,
        {
            "use_blueprint": {
                "path": "edisio/ebp8b_controller.yaml",
                "input": {
                    "edisio_device": "0123456789abcdef0123456789abcdef",
                    "button_05_short": [{"event": "button_05_short_pressed"}],
                    "button_08_long": [{"event": "button_08_long_pressed"}],
                },
            }
        },
    )
    inputs.validate()

    config = await async_validate_config_item(hass, "edisio_test", inputs.async_substitute())

    (trigger,) = config["triggers"]
    assert [t.template for t in trigger["event_type"]] == ["edisio_button_event"]
    assert len(config["conditions"]) == 1
    (choose,) = [step for step in config["actions"] if "choose" in step]
    sequences = {
        branch["conditions"][0]["value_template"].template: branch["sequence"]
        for branch in choose["choose"]
    }
    assert sequences["{{ button == '05' and press_type == 'short_press' }}"] == [
        {"event": "button_05_short_pressed"}
    ]
    assert sequences["{{ button == '08' and press_type == 'long_press' }}"] == [
        {"event": "button_08_long_pressed"}
    ]
    assert sequences["{{ button == '01' and press_type == 'short_press' }}"] == []
