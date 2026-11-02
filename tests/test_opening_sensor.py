"""An Opening sensor shows Open/Closed and Battery, replaying frames recorded from Device 91107A5D."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.edisio import async_setup_entry, binary_sensor, sensor
from custom_components.edisio.const import DOMAIN
from custom_components.edisio.edisio_api import decode_packet

pytestmark = pytest.mark.asyncio

SENSOR = "91107A5D"
# Model code 09, Button number 01 (meaningless), the byte after the battery is 05.
CLOSED_01 = "6C766391107A5D01091C0500" "01" "640D0A"
CLOSED_09 = "6C766391107A5D01091C0500" "09" "640D0A"
OPEN_02 = "6C766391107A5D01091C0500" "02" "640D0A"
OPEN_0A = "6C766391107A5D01091C0500" "0A" "640D0A"
SENSOR_BUTTON_2F = "6C766391107A5D01091405002F640D0A"  # lower battery byte: 0x14 -> 60 %
PLATE = "06709603"
PLATE_PRESS = "6C76630670960305011C010003640D0A"


@pytest_asyncio.fixture
async def replay(hass, add_config_entry, set_up_platform):
    """Feed hex frames through the integration; return a feed function plus the fired events."""
    entry = add_config_entry(
        data={"serial_port": "/dev/ttyUSB0"},
        options={"devices": {
            SENSOR: {"device_model": "opening_sensor"},
            PLATE: {"active_buttons": 5},
        }},
    )
    events = []
    hass.bus.async_listen("edisio_button_event", lambda e: events.append(e.data))

    now = [1000.0]
    with patch("custom_components.edisio.EdisioHub") as hub_class, \
         patch("custom_components.edisio.press.monotonic", lambda: now[0]), \
         patch.object(hass.config_entries, "async_forward_entry_setups", AsyncMock()):
        hub = MagicMock()
        hub.connect = AsyncMock()
        hub_class.return_value = hub
        await async_setup_entry(hass, entry)
        await set_up_platform(entry, sensor, "sensor")
        await set_up_platform(entry, binary_sensor, "binary_sensor")
        callback = hub.register_callback.call_args[0][0]

        async def feed(*frames: str) -> None:
            for frame in frames:
                callback(decode_packet(frame))
                await hass.async_block_till_done()
                now[0] += 0.024  # frames of a burst are ~24 ms apart

        feed.pause = lambda: now.__setitem__(0, now[0] + 5)
        feed.events = events
        yield feed


def _state(hass, domain: str, unique_id: str):
    entity_id = er.async_get(hass).async_get_entity_id(domain, DOMAIN, unique_id)
    assert entity_id is not None, f"no {domain} entity for {unique_id}"
    return hass.states.get(entity_id)


async def test_never_reported_sensor_is_unknown(hass, replay):
    assert _state(hass, "binary_sensor", f"{SENSOR}_opening").state == "unknown"


@pytest.mark.parametrize("frame", [CLOSED_01, CLOSED_09])
async def test_either_closed_command_gives_closed(hass, replay, frame):
    await replay(OPEN_02)
    await replay(frame)
    assert _state(hass, "binary_sensor", f"{SENSOR}_opening").state == "off"


@pytest.mark.parametrize("frame", [OPEN_02, OPEN_0A])
async def test_either_open_command_gives_open(hass, replay, frame):
    await replay(CLOSED_01)
    await replay(frame)
    assert _state(hass, "binary_sensor", f"{SENSOR}_opening").state == "on"


async def test_burst_with_one_command_lost_still_transitions(hass, replay):
    await replay(CLOSED_01, CLOSED_09, CLOSED_01)
    replay.pause()
    await replay(OPEN_02, OPEN_02, OPEN_02)  # 0A lost
    assert _state(hass, "binary_sensor", f"{SENSOR}_opening").state == "on"
    replay.pause()
    await replay(CLOSED_09, CLOSED_09)  # 01 lost
    assert _state(hass, "binary_sensor", f"{SENSOR}_opening").state == "off"


async def test_sensor_button_updates_battery_only(hass, replay):
    await replay(OPEN_02)
    await replay(SENSOR_BUTTON_2F)
    assert _state(hass, "binary_sensor", f"{SENSOR}_opening").state == "on"
    assert _state(hass, "sensor", f"{SENSOR}_battery").state == "60"


async def test_opening_sensor_fires_no_button_event_and_has_no_button_sensors(hass, replay):
    await replay(CLOSED_01, CLOSED_09, OPEN_02, OPEN_0A, SENSOR_BUTTON_2F)
    assert replay.events == []
    ids = sorted(e.unique_id for e in er.async_get(hass).entities.values() if e.unique_id.startswith(SENSOR))
    assert ids == [f"{SENSOR}_battery", f"{SENSOR}_opening"]


async def test_opening_sensor_is_an_opening_class_device_named_by_default(hass, replay):
    state = _state(hass, "binary_sensor", f"{SENSOR}_opening")
    assert state.attributes["device_class"] == "opening"
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, SENSOR)})
    assert device.model == "Opening sensor"
    assert device.name == f"Edisio Opening sensor {SENSOR}"
    assert device.via_device_id is not None


async def test_wall_plate_frames_behave_as_before(hass, replay):
    await replay(PLATE_PRESS)
    assert replay.events == [{"device_id": PLATE, "button": "05", "type": "short_press"}]
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, PLATE)})
    assert device.model == "EBP8"
