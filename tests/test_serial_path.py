"""The Dongle is stored by its stable /dev/serial/by-id path, not /dev/ttyUSBn (edisio-3yx)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.edisio import async_migrate_entry
from custom_components.edisio.config_flow import EdisioConfigFlow

BY_ID = "/dev/serial/by-id/usb-FTDI_Edisio-if00-port0"
RAW = "/dev/ttyUSB1"

pytestmark = pytest.mark.asyncio


def _flow():
    flow = EdisioConfigFlow()
    flow.hass = MagicMock(spec=HomeAssistant)
    flow._async_current_entries = MagicMock(return_value=[])
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    return flow


def _resolve(path):
    return BY_ID if path == RAW else path


async def test_usb_discovery_stores_by_id_path():
    flow = _flow()
    with patch("custom_components.edisio.config_flow.usb.get_serial_by_id", _resolve):
        await flow.async_step_usb(MagicMock(device=RAW))
        result = await flow.async_step_usb_confirm(user_input={})
    assert result["data"] == {"serial_port": BY_ID}
    flow.async_set_unique_id.assert_called_once_with(BY_ID)


async def test_manual_setup_stores_by_id_path():
    flow = _flow()
    with patch("custom_components.edisio.config_flow.usb.get_serial_by_id", _resolve):
        result = await flow.async_step_user({"serial_port": RAW})
    assert result["data"] == {"serial_port": BY_ID}


async def test_manual_setup_keeps_path_without_by_id_link():
    flow = _flow()
    with patch("custom_components.edisio.config_flow.usb.get_serial_by_id", lambda p: p):
        result = await flow.async_step_user({"serial_port": "/dev/ttyAMA0"})
    assert result["data"] == {"serial_port": "/dev/ttyAMA0"}


async def test_existing_entry_is_migrated_to_by_id_path():
    hass = MagicMock(spec=HomeAssistant)
    entry = MagicMock(version=1, data={"serial_port": RAW}, unique_id=RAW)
    with patch("custom_components.edisio.usb.get_serial_by_id", _resolve):
        assert await async_migrate_entry(hass, entry) is True
    hass.config_entries.async_update_entry.assert_called_once_with(
        entry, data={"serial_port": BY_ID}, unique_id=BY_ID, version=2
    )
