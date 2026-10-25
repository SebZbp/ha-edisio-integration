"""Shared fixtures for tests that run against a real (minimal) HomeAssistant."""
import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta

import pytest
import pytest_asyncio
from homeassistant import config_entries, loader
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import EntityPlatform

from custom_components.edisio import sensor
from custom_components.edisio.const import DOMAIN


@pytest_asyncio.fixture
async def hass(tmp_path):
    """A real HomeAssistant with config entries and the device/entity registries loaded."""
    hass = HomeAssistant(str(tmp_path))
    loader.async_setup(hass)  # integration loader, needed to validate automation config
    hass.config_entries = config_entries.ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    await ar.async_load(hass)
    await dr.async_load(hass)
    await er.async_load(hass)
    yield hass
    await hass.async_stop(force=True)


@pytest.fixture
def add_config_entry(hass) -> Callable[..., config_entries.ConfigEntry]:
    """Register an Edisio config entry without running the integration's setup (no Dongle)."""

    def _add(*, data: dict | None = None, options: dict | None = None) -> config_entries.ConfigEntry:
        entry = config_entries.ConfigEntry(
            version=1,
            minor_version=1,
            domain=DOMAIN,
            title="Edisio",
            data=data or {},
            options=options or {},
            source=config_entries.SOURCE_USER,
            unique_id=None,
            discovery_keys={},
        )
        hass.config_entries._entries[entry.entry_id] = entry
        return entry

    return _add


@pytest.fixture
def set_up_sensor_platform(hass) -> Callable[[config_entries.ConfigEntry], Awaitable[None]]:
    """Run the Edisio sensor platform for ``entry``, as HA would after the entry's setup."""

    async def _set_up(entry: config_entries.ConfigEntry) -> None:
        hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {"devices": set()})
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

    return _set_up
