"""Button sensor naming, seen through the entity registry (spec: stable-button-naming)."""
import logging
from datetime import timedelta

import pytest
import pytest_asyncio
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import EntityPlatform

from custom_components.edisio import sensor
from custom_components.edisio.const import DOMAIN


@pytest_asyncio.fixture
async def hass(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    hass.config_entries = config_entries.ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    await dr.async_load(hass)
    await er.async_load(hass)
    yield hass
    await hass.async_stop(force=True)


async def _set_up_sensors(hass: HomeAssistant, devices: dict) -> er.EntityRegistry:
    """Run the sensor platform for a config entry holding ``devices``."""
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Edisio",
        data={"serial_port": "/dev/null"},
        options={"devices": devices},
        source=config_entries.SOURCE_USER,
        unique_id=None,
        discovery_keys={},
    )
    # Register the entry without running the integration's own setup (no dongle).
    hass.config_entries._entries[entry.entry_id] = entry
    hass.data[DOMAIN] = {entry.entry_id: {"devices": set()}}
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, entry.entry_id)}
    )
    platform = EntityPlatform(
        hass=hass,
        logger=logging.getLogger(__name__),
        domain="sensor",
        platform_name=DOMAIN,
        platform=sensor,
        scan_interval=timedelta(seconds=30),
        entity_namespace=None,
    )
    platform.config_entry = entry
    await platform.async_setup_entry(entry)
    await hass.async_block_till_done()
    return er.async_get(hass)


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
async def test_button_sensors_named_by_button_number(hass, layout, button_numbers):
    registry = await _set_up_sensors(hass, {"04997264": {"active_buttons": layout}})

    entries = _button_entries(registry, "04997264")

    assert [e.unique_id for e in entries] == [f"04997264_button_{n}" for n in button_numbers]
    assert [e.original_name for e in entries] == [f"Button {n}" for n in button_numbers]


@pytest.mark.asyncio
async def test_new_device_gets_entity_ids_ending_in_button_number(hass):
    registry = await _set_up_sensors(hass, {"06708DE5": {"active_buttons": 5}})

    entity_ids = [e.entity_id for e in _button_entries(registry, "06708DE5")]

    assert entity_ids == [
        "sensor.edisio_ebp8_b_06708de5_button_01",
        "sensor.edisio_ebp8_b_06708de5_button_03",
        "sensor.edisio_ebp8_b_06708de5_button_05",
        "sensor.edisio_ebp8_b_06708de5_button_07",
        "sensor.edisio_ebp8_b_06708de5_button_08",
    ]


@pytest.mark.asyncio
async def test_existing_entity_id_kept_on_upgrade_and_name_follows_button_number(hass):
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        "04997264_button_03",
        suggested_object_id="edisio_ebp8_b_04997264_button_2",
        original_name="Button 2",
    )

    registry = await _set_up_sensors(hass, {"04997264": {"active_buttons": 5}})

    entity_id = registry.async_get_entity_id("sensor", DOMAIN, "04997264_button_03")
    assert entity_id == "sensor.edisio_ebp8_b_04997264_button_2"
    assert registry.async_get(entity_id).original_name == "Button 03"
