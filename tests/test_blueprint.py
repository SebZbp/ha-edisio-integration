"""The automation blueprint, checked against the Button layouts (spec: blueprint-button-numbers)."""
import re
from pathlib import Path

import pytest
import pytest_asyncio
from homeassistant import config_entries
from homeassistant.components.blueprint.models import Blueprint
from homeassistant.components.blueprint.schemas import BLUEPRINT_SCHEMA
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.template import Template
from homeassistant.util.yaml import load_yaml

from custom_components.edisio.const import BUTTON_CONFIGS, DOMAIN

BLUEPRINT_PATH = (
    Path(__file__).parent.parent / "blueprints" / "automation" / "edisio" / "ebp8b_controller.yaml"
)

ALL_BUTTON_NUMBERS = {"01", "02", "03", "04", "05", "06", "07", "08"}


@pytest.fixture
def blueprint() -> Blueprint:
    return Blueprint(
        load_yaml(BLUEPRINT_PATH),
        expected_domain="automation",
        schema=BLUEPRINT_SCHEMA,
    )


def _choose_branches(blueprint: Blueprint) -> list[dict]:
    for step in blueprint.data["actions"] if "actions" in blueprint.data else blueprint.data["action"]:
        if "choose" in step:
            return step["choose"]
    raise AssertionError("blueprint has no choose step")


def test_layout_union_is_every_button_number():
    # Guards the hand-written literal used below against the real layouts.
    assert set().union(*BUTTON_CONFIGS.values()) == ALL_BUTTON_NUMBERS


def test_blueprint_handles_exactly_the_button_numbers_of_all_layouts(blueprint):
    handled = set()
    for branch in _choose_branches(blueprint):
        for condition in branch["conditions"]:
            handled.update(re.findall(r"button == '(\d\d)'", condition))
    assert handled == set().union(*BUTTON_CONFIGS.values())


def test_blueprint_has_short_and_long_action_per_button_in_sections(blueprint):
    sections = {
        key: value for key, value in blueprint.data["blueprint"]["input"].items()
        if "input" in value
    }
    for number in sorted(ALL_BUTTON_NUMBERS):
        section = sections[f"button_{number}"]
        assert section["name"] == f"Button {number}"
        assert section["collapsed"] is True
        assert set(section["input"]) == {f"button_{number}_short", f"button_{number}_long"}
        for key in section["input"]:
            assert section["input"][key]["default"] == []
            assert "action" in section["input"][key]["selector"]


def test_section_descriptions_name_the_layouts_containing_the_button(blueprint):
    inputs = blueprint.data["blueprint"]["input"]
    for number in sorted(ALL_BUTTON_NUMBERS):
        description = inputs[f"button_{number}"]["description"]
        for layout, numbers in BUTTON_CONFIGS.items():
            mentioned = f"{layout}-Button" in description
            assert mentioned == (number in numbers), (number, layout, description)


def test_every_branch_runs_its_matching_input(blueprint):
    for branch in _choose_branches(blueprint):
        (condition,) = branch["conditions"]
        number, press = re.fullmatch(
            r"\{\{ button == '(\d\d)' and press_type == '(short|long)_press' \}\}", condition
        ).groups()
        assert branch["sequence"].name == f"button_{number}_{press}"


def test_device_is_picked_from_edisio_devices(blueprint):
    device_input = blueprint.data["blueprint"]["input"]["edisio_device"]
    assert device_input["selector"]["device"]["filter"] == [{"integration": "edisio"}]
    assert "edisio_device_id" not in blueprint.inputs


def test_requires_ha_version_with_input_sections(blueprint):
    assert blueprint.data["blueprint"]["homeassistant"]["min_version"] == "2024.6.0"
    assert blueprint.data["mode"] == "queued"


@pytest_asyncio.fixture
async def hass(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    hass.config_entries = config_entries.ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    await dr.async_load(hass)
    yield hass
    await hass.async_stop(force=True)


@pytest.mark.asyncio
async def test_radio_id_is_derived_from_the_selected_device(hass, blueprint):
    entry = config_entries.ConfigEntry(
        version=1, minor_version=1, domain=DOMAIN, title="Edisio",
        data={}, options={}, source=config_entries.SOURCE_USER,
        unique_id=None, discovery_keys={},
    )
    hass.config_entries._entries[entry.entry_id] = entry
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "06709603")},
        name="BP Bas escalier",
    )
    radio_id = Template(blueprint.data["variables"]["radio_id"], hass).async_render(
        {"edisio_device": device.id}
    )
    assert radio_id == "06709603"
