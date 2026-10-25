"""Button sensor naming, seen through the entity registry (spec: stable-button-naming)."""

import pytest
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.edisio.const import DOMAIN


@pytest.fixture
def set_up_sensors(hass, add_config_entry, set_up_sensor_platform):
    """Run the sensor platform for a config entry holding ``devices``; return the entity registry."""

    async def _set_up(devices: dict) -> er.EntityRegistry:
        entry = add_config_entry(data={"serial_port": "/dev/null"}, options={"devices": devices})
        # Parent Dongle device, normally registered by the integration's own setup.
        dr.async_get(hass).async_get_or_create(
            config_entry_id=entry.entry_id, identifiers={(DOMAIN, entry.entry_id)}
        )
        await set_up_sensor_platform(entry)
        return er.async_get(hass)

    return _set_up


def _button_entries(registry: er.EntityRegistry, radio_id: str) -> list[er.RegistryEntry]:
    return sorted(
        (e for e in registry.entities.values()
         if e.unique_id.startswith(f"{radio_id}_button_")),
        key=lambda e: e.unique_id,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("layout", "button_numbers"),
    [
        (1, ["05"]),
        (2, ["04", "06"]),
        (3, ["02", "07", "08"]),
        (4, ["01", "03", "07", "08"]),
        (5, ["01", "03", "05", "07", "08"]),
    ],
)
async def test_button_sensors_named_by_button_number(set_up_sensors, layout, button_numbers):
    registry = await set_up_sensors({"04997264": {"active_buttons": layout}})

    entries = _button_entries(registry, "04997264")

    assert [e.unique_id for e in entries] == [f"04997264_button_{n}" for n in button_numbers]
    assert [e.original_name for e in entries] == [f"Button {n}" for n in button_numbers]


@pytest.mark.asyncio
async def test_new_device_gets_entity_ids_ending_in_button_number(set_up_sensors):
    registry = await set_up_sensors({"06708DE5": {"active_buttons": 5}})

    entity_ids = [e.entity_id for e in _button_entries(registry, "06708DE5")]

    assert entity_ids == [
        "sensor.edisio_ebp8_b_06708de5_button_01",
        "sensor.edisio_ebp8_b_06708de5_button_03",
        "sensor.edisio_ebp8_b_06708de5_button_05",
        "sensor.edisio_ebp8_b_06708de5_button_07",
        "sensor.edisio_ebp8_b_06708de5_button_08",
    ]


@pytest.mark.asyncio
async def test_existing_entity_id_kept_on_upgrade_and_name_follows_button_number(hass, set_up_sensors):
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        "04997264_button_03",
        suggested_object_id="edisio_ebp8_b_04997264_button_2",
        original_name="Button 2",
    )

    registry = await set_up_sensors({"04997264": {"active_buttons": 5}})

    entity_id = registry.async_get_entity_id("sensor", DOMAIN, "04997264_button_03")
    assert entity_id == "sensor.edisio_ebp8_b_04997264_button_2"
    assert registry.async_get(entity_id).original_name == "Button 03"
