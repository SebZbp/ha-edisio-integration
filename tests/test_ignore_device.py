"""Ignoring a Device from its Discovery card with HA's native Ignore (edisio-bxi)."""
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.edisio import async_setup_entry
from custom_components.edisio.const import DOMAIN

pytestmark = pytest.mark.asyncio

RADIO_ID = "0670A248"


@pytest.fixture
def dongle(add_config_entry):
    return add_config_entry(data={"serial_port": "/dev/ttyUSB0"})


def _add_ignored(hass, radio_id=RADIO_ID):
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title=f"Edisio Wall plate {radio_id}",
        data={},
        options={},
        source=config_entries.SOURCE_IGNORE,
        unique_id=f"edisio_{radio_id}",
        discovery_keys={},
    )
    hass.config_entries._entries[entry.entry_id] = entry
    return entry


async def _discover(hass, model_code="01", radio_id=RADIO_ID):
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY, "device_id": radio_id},
        data={"device_id": radio_id, "button": "05", "model_code": model_code},
    )


def _cards(hass):
    return [f for f in hass.config_entries.flow.async_progress() if f["handler"] == DOMAIN]


@pytest.mark.parametrize("model_code, title", [
    ("01", "Edisio Wall plate 0670A248"),
    ("09", "Edisio Opening sensor 0670A248"),
    ("18", "Edisio unknown Device 0670A248 (Model code 18)"),
])
async def test_card_is_titled_by_device_model(hass, dongle, model_code, title):
    await _discover(hass, model_code)
    [card] = _cards(hass)
    assert card["context"]["title_placeholders"] == {"name": title}


async def test_card_is_a_discovery_with_a_unique_id_so_ha_offers_ignore(hass, dongle):
    await _discover(hass)
    [card] = _cards(hass)
    assert card["context"]["source"] in config_entries.DISCOVERY_SOURCES
    assert card["context"]["unique_id"] == f"edisio_{RADIO_ID}"


async def test_ignoring_the_card_stores_an_ignored_entry_and_closes_the_card(hass, dongle):
    await _discover(hass)
    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IGNORE},
        data={"unique_id": f"edisio_{RADIO_ID}", "title": "Edisio Wall plate 0670A248"},
    )
    assert not _cards(hass)
    ignored = hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, f"edisio_{RADIO_ID}")
    assert ignored.source == config_entries.SOURCE_IGNORE
    assert ignored.title == "Edisio Wall plate 0670A248"
    # A later card for the same Device is refused
    result = await _discover(hass)
    assert result["type"] == data_entry_flow.FlowResultType.ABORT


async def test_submitting_a_card_updates_the_dongle_not_an_ignored_entry(add_config_entry, hass):
    ignored = _add_ignored(hass, "91107A5D")  # registered before the Dongle
    dongle = add_config_entry(data={"serial_port": "/dev/ttyUSB0"})
    result = await _discover(hass)
    await hass.config_entries.flow.async_configure(result["flow_id"], {"active_buttons": 3})
    assert dongle.options["devices"] == {RADIO_ID: {"active_buttons": 3}}
    assert ignored.options == {}


async def test_usb_discovery_does_not_count_an_ignored_entry_as_a_dongle(hass):
    _add_ignored(hass)
    with patch("custom_components.edisio.config_flow.usb.get_serial_by_id", lambda p: p):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USB},
            data=MagicMock(device="/dev/ttyUSB0"),
        )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "usb_confirm"


async def test_adding_an_ignored_device_by_hand_clears_the_ignore(hass, dongle):
    _add_ignored(hass)
    result = await hass.config_entries.options.async_init(dongle.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_device"}
    )
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"radio_id": RADIO_ID})
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert RADIO_ID in dongle.options["devices"]
    assert hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, f"edisio_{RADIO_ID}") is None


async def _packet_handler(ignored_ids):
    """Set up the integration on a mocked hass; return its packet callback and hass."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.bus = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.flow.async_progress = MagicMock(return_value=[])
    hass.config_entries.flow.async_init = MagicMock()
    hass.config_entries.async_entry_for_domain_unique_id = MagicMock(
        side_effect=lambda domain, uid: (
            MagicMock(source=config_entries.SOURCE_IGNORE) if uid[len("edisio_"):] in ignored_ids else None
        )
    )
    hass.loop = MagicMock()
    hass.loop.call_soon_threadsafe = lambda func, *args: func(*args)
    entry = MagicMock(spec=config_entries.ConfigEntry)
    entry.data = {"serial_port": "/dev/ttyUSB0"}
    entry.options = {}
    entry.entry_id = "dongle"
    with patch("custom_components.edisio.EdisioHub") as mock_hub_class, \
         patch("homeassistant.helpers.device_registry.async_get"):
        hub = mock_hub_class.return_value
        hub.connect = AsyncMock()
        await async_setup_entry(hass, entry)
    return hub.register_callback.call_args[0][0], hass


async def test_ignored_device_packets_start_no_flow_but_stay_in_the_debug_log(caplog):
    ignored_ids = {RADIO_ID}
    callback, hass = await _packet_handler(ignored_ids)
    caplog.set_level(logging.DEBUG, logger="custom_components.edisio")
    callback({"id": RADIO_ID, "button": "05", "mid": "01", "cmd": "01", "action": "1"})
    hass.config_entries.flow.async_init.assert_not_called()
    hass.bus.async_fire.assert_not_called()
    assert "Press received" in caplog.text and "'mid': '01'" in caplog.text
    assert f"Dropping packet from Ignored Device {RADIO_ID}" in caplog.text

    # Stop ignoring is read live: the next packet raises a card again
    ignored_ids.clear()
    callback({"id": RADIO_ID, "button": "05", "mid": "01", "cmd": "02", "action": "0"})
    hass.config_entries.flow.async_init.assert_called_once()
