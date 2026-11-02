from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import EntityCategory
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.edisio import async_setup_entry
from custom_components.edisio.const import DOMAIN
from .conftest import wait_until


@pytest.mark.asyncio
async def test_connection_entity_follows_the_dongle(
    hass, add_config_entry, set_up_binary_sensor_platform, dongle
):
    entry = add_config_entry(data={"serial_port": "/dev/null"})
    with patch.object(hass.config_entries, "async_forward_entry_setups", AsyncMock()) as forward:
        assert await async_setup_entry(hass, entry)
    forward.assert_awaited_once_with(entry, ["sensor", "binary_sensor"])
    await set_up_binary_sensor_platform(entry)

    entity_id = er.async_get(hass).async_get_entity_id(
        "binary_sensor", DOMAIN, f"{entry.entry_id}_connection"
    )
    assert hass.states.get(entity_id).state == "on"

    dongle.unplug()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "off"

    dongle.replug()
    await wait_until(lambda: hass.states.get(entity_id).state == "on")

    await hass.data[DOMAIN][entry.entry_id]["hub"].disconnect()


@pytest.mark.asyncio
async def test_connection_entity_is_a_diagnostic_of_the_dongle(
    hass, add_config_entry, set_up_binary_sensor_platform, dongle
):
    entry = add_config_entry(data={"serial_port": "/dev/null"})
    with patch.object(hass.config_entries, "async_forward_entry_setups", AsyncMock()):
        await async_setup_entry(hass, entry)
    await set_up_binary_sensor_platform(entry)

    registry = er.async_get(hass)
    entity = registry.async_get(
        registry.async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_connection")
    )
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert entity.device_id == device.id
    assert entity.entity_category is EntityCategory.DIAGNOSTIC
    assert entity.original_device_class == "connectivity"

    await hass.data[DOMAIN][entry.entry_id]["hub"].disconnect()
