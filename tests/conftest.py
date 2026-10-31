"""Shared fixtures for tests that run against a real (minimal) HomeAssistant."""
import asyncio
import itertools
import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from homeassistant import config_entries, loader
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import EntityPlatform
from serial import SerialException

from custom_components.edisio import binary_sensor, sensor
from custom_components.edisio.const import DOMAIN


class FakeDongle:
    """Stands in for the serial port: opens like create_serial_connection and can be unplugged."""

    def __init__(self):
        self.plugged_in = True
        self.open_attempts = 0
        self.protocol = None
        self.transport = None

    async def open(self, loop, protocol_factory, port, **kwargs):
        self.open_attempts += 1
        if not self.plugged_in:
            raise SerialException(f"could not open port {port}")
        protocol = protocol_factory()
        transport = MagicMock()
        transport.close.side_effect = lambda: protocol.connection_lost(None)
        protocol.connection_made(transport)
        self.protocol, self.transport = protocol, transport
        return transport, protocol

    def unplug(self):
        self.plugged_in = False
        self.protocol.connection_lost(SerialException("device disconnected"))

    def replug(self):
        self.plugged_in = True


@pytest.fixture
def dongle():
    """A plugged-in FakeDongle behind the serial layer, with near-instant reconnect delays."""
    dongle = FakeDongle()
    with patch("serial_asyncio_fast.create_serial_connection", dongle.open), \
         patch("custom_components.edisio.hub._reconnect_delays", lambda: itertools.repeat(0.001)):
        yield dongle


async def wait_until(condition: Callable[[], bool]) -> None:
    async with asyncio.timeout(1):
        while not condition():
            await asyncio.sleep(0.001)


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


async def _set_up_platform(hass, entry: config_entries.ConfigEntry, domain: str, module) -> None:
    """Run an Edisio entity platform for ``entry``, as HA would after the entry's setup."""
    hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {"devices": set()})
    platform = EntityPlatform(
        hass=hass,
        logger=logging.getLogger(__name__),
        domain=domain,
        platform_name=DOMAIN,
        platform=module,
        scan_interval=timedelta(seconds=30),
        entity_namespace=None,
    )
    platform.config_entry = entry
    await platform.async_setup_entry(entry)
    await hass.async_block_till_done()


@pytest.fixture
def set_up_sensor_platform(hass) -> Callable[[config_entries.ConfigEntry], Awaitable[None]]:
    """Run the Edisio sensor platform for ``entry``, as HA would after the entry's setup."""

    async def _set_up(entry: config_entries.ConfigEntry) -> None:
        await _set_up_platform(hass, entry, "sensor", sensor)

    return _set_up


@pytest.fixture
def set_up_binary_sensor_platform(hass) -> Callable[[config_entries.ConfigEntry], Awaitable[None]]:
    """Run the Edisio binary_sensor platform for ``entry``, as HA would after the entry's setup."""

    async def _set_up(entry: config_entries.ConfigEntry) -> None:
        await _set_up_platform(hass, entry, "binary_sensor", binary_sensor)

    return _set_up
