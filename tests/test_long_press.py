"""One physical press = one edisio_button_event, replaying packets captured on Device 06709603 (edisio-s4h.2)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.edisio import async_setup_entry
from custom_components.edisio.edisio_api import decode_packet

pytestmark = pytest.mark.asyncio

DEVICE = "06709603"
SHORT_05 = ["6C76630670960305011C010003640D0A", "6C76630670960305011C010103640D0A"] * 2
SHORT_07 = [p.replace("0305", "0307") for p in SHORT_05]
HOLD_05 = "6C76630670960305011C000007640D0A"
HOLD_07 = "6C76630670960307011C000007640D0A"


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest_asyncio.fixture
async def replay():
    """Feed hex packets at given times through the integration; return the fired events."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.bus = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.loop = MagicMock()
    hass.loop.call_soon_threadsafe = lambda func, *args: func(*args)
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {"serial_port": "/dev/ttyUSB0"}
    entry.options = {"devices": {DEVICE: {"active_buttons": 5}}}
    entry.entry_id = "e"
    clock = Clock()

    with patch("custom_components.edisio.EdisioHub") as hub_class, \
         patch("homeassistant.helpers.device_registry.async_get"), \
         patch("custom_components.edisio.press.monotonic", clock):
        hub = MagicMock()
        hub.connect = AsyncMock()
        hub_class.return_value = hub
        await async_setup_entry(hass, entry)
        callback = hub.register_callback.call_args[0][0]

        def feed(packets: list[str], *, gap: float = 0.024) -> list[tuple[str, str]]:
            """Send packets ``gap`` s apart; return (button, type) events fired by this call."""
            before = hass.bus.async_fire.call_count
            for p in packets:
                callback(decode_packet(p))
                clock.now += gap
            return [
                (c.args[1]["button"], c.args[1]["type"])
                for c in hass.bus.async_fire.call_args_list[before:]
            ]

        feed.clock = clock
        yield feed


async def test_short_press_burst_fires_one_short_press(replay):
    assert replay(SHORT_05, gap=0.02) == [("05", "short_press")]


async def test_hold_fires_one_long_press(replay):
    assert replay([HOLD_07] * 150) == [("07", "long_press")]


async def test_hold_then_release_fires_no_short_press(replay):
    assert replay([HOLD_05] * 27) == [("05", "long_press")]


async def test_two_quick_short_presses_fire_two_events(replay):
    first = replay(SHORT_05)
    replay.clock.now += 0.4
    assert first + replay(SHORT_05) == [("05", "short_press")] * 2


async def test_holds_on_two_buttons_fire_one_long_press_each(replay):
    events = []
    for _ in range(20):
        events += replay([HOLD_05, HOLD_07], gap=0.012)
    assert sorted(events) == [("05", "long_press"), ("07", "long_press")]


async def test_second_hold_after_pause_fires_again(replay):
    events = replay([HOLD_05] * 10)
    replay.clock.now += 2
    assert events + replay([HOLD_05] * 10) == [("05", "long_press")] * 2


async def test_press_after_hold_on_same_button_is_a_new_event(replay):
    events = replay([HOLD_05] * 10)
    replay.clock.now += 0.4
    assert events + replay(SHORT_05) == [("05", "long_press"), ("05", "short_press")]
