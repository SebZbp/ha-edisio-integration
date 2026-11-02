import asyncio
import itertools
import pytest
from serial import SerialException
from unittest.mock import patch, MagicMock, AsyncMock
from custom_components.edisio.hub import EdisioHub, EdisioProtocol, _reconnect_delays
from .conftest import wait_until

PACKET = b"\x6c\x76\x63\x00\x00\x00\x01\x01\x01\x2e\x00\x00\x03\x64\x0d\x0a"


@pytest.mark.asyncio
async def test_edisio_hub_connect():
    hub = EdisioHub(port="/dev/ttyUSB0")
    
    with patch("serial_asyncio_fast.create_serial_connection") as mock_create_connection:
        mock_transport = MagicMock()
        mock_protocol = EdisioProtocol()
        mock_create_connection.return_value = (mock_transport, mock_protocol)
        
        await hub.connect()
        
        mock_create_connection.assert_called_once()
        assert hub._transport is mock_transport
        assert hub._protocol is mock_protocol

def test_edisio_protocol_buffering():
    callback = MagicMock()
    protocol = EdisioProtocol(callback)
    
    # Send a partial packet
    protocol.data_received(b"\x6c\x76\x63\x00\x00\x00")
    callback.assert_not_called()
    
    # Complete the packet
    protocol.data_received(b"\x01\x01\x01\x2e\x00\x00\x03\x64\x0d\x0a")
    callback.assert_called_once_with("6C76630000000101012E000003640D0A")
    
    # Send multiple packets at once
    callback.reset_mock()
    protocol.data_received(
        b"\x6c\x76\x63\x00\x00\x00\x01\x01\x01\x2e\x00\x00\x03\x64\x0d\x0a\x6c\x76\x63\x00"
    )
    callback.assert_called_once_with("6C76630000000101012E000003640D0A")


@pytest.mark.asyncio
async def test_edisio_hub_disconnect_closes_transport_and_drops_callbacks():
    hub = EdisioHub(port="/dev/ttyUSB0")
    protocol = EdisioProtocol()
    transport = MagicMock()
    transport.close.side_effect = lambda: protocol.connection_lost(None)
    with patch("serial_asyncio_fast.create_serial_connection", return_value=(transport, protocol)):
        await hub.connect()
    hub.register_callback(MagicMock())

    await hub.disconnect()

    transport.close.assert_called_once()
    assert hub._transport is None
    assert hub._protocol is None
    assert hub.callbacks == []


@pytest.mark.asyncio
async def test_edisio_hub_disconnect_awaits_connection_lost():
    hub = EdisioHub(port="/dev/ttyUSB0")
    protocol = EdisioProtocol()
    transport = MagicMock()
    transport.close.side_effect = lambda: asyncio.get_running_loop().call_soon(protocol.connection_lost, None)
    with patch("serial_asyncio_fast.create_serial_connection", return_value=(transport, protocol)):
        await hub.connect()

    await asyncio.wait_for(hub.disconnect(), timeout=1)

    assert protocol.closed.is_set()


@pytest.mark.asyncio
async def test_edisio_hub_disconnect_without_connect_is_noop():
    await EdisioHub(port="/dev/ttyUSB0").disconnect()


@pytest.mark.asyncio
async def test_presses_are_received_again_after_the_dongle_is_replugged(dongle):
    hub = EdisioHub(port="/dev/ttyUSB0")
    received = MagicMock()
    hub.register_callback(received)
    await hub.connect()

    dongle.unplug()
    dongle.replug()
    await wait_until(lambda: dongle.open_attempts == 2)
    dongle.protocol.data_received(PACKET)

    received.assert_called_once()
    await hub.disconnect()


@pytest.mark.asyncio
async def test_hub_keeps_trying_until_the_dongle_comes_back(dongle):
    hub = EdisioHub(port="/dev/ttyUSB0")
    await hub.connect()

    dongle.unplug()
    await wait_until(lambda: dongle.open_attempts >= 5)
    assert not hub.connected
    dongle.replug()
    await wait_until(lambda: hub.connected)

    await hub.disconnect()


def test_reconnect_delays_double_up_to_a_minute():
    assert list(itertools.islice(_reconnect_delays(), 8)) == [1, 2, 4, 8, 16, 32, 60, 60]


@pytest.mark.asyncio
async def test_disconnect_during_an_outage_stops_retrying(dongle):
    hub = EdisioHub(port="/dev/ttyUSB0")
    await hub.connect()
    dongle.unplug()
    await wait_until(lambda: dongle.open_attempts >= 2)

    await asyncio.wait_for(hub.disconnect(), timeout=1)
    attempts = dongle.open_attempts
    dongle.replug()
    await asyncio.sleep(0.02)

    assert dongle.open_attempts == attempts
    assert hub._transport is None


@pytest.mark.asyncio
async def test_disconnect_does_not_trigger_a_reconnect(dongle):
    hub = EdisioHub(port="/dev/ttyUSB0")
    await hub.connect()

    await hub.disconnect()
    await asyncio.sleep(0.02)

    assert dongle.open_attempts == 1


@pytest.mark.asyncio
async def test_disconnect_while_the_port_is_reopening_leaves_it_closed(dongle):
    hub = EdisioHub(port="/dev/ttyUSB0")
    await hub.connect()
    release_open = asyncio.Event()
    open_port = dongle.open

    async def slow_open(*args, **kwargs):
        result = await open_port(*args, **kwargs)
        await release_open.wait()
        return result

    with patch("serial_asyncio_fast.create_serial_connection", slow_open):
        dongle.plugged_in = False
        dongle.protocol.connection_lost(SerialException("device disconnected"))
        dongle.replug()
        await wait_until(lambda: dongle.open_attempts == 2)
        disconnecting = asyncio.ensure_future(hub.disconnect())
        await asyncio.sleep(0.01)
        release_open.set()
        await asyncio.wait_for(disconnecting, timeout=1)

    dongle.transport.close.assert_called_once()
    assert hub._transport is None


@pytest.mark.asyncio
async def test_connection_callbacks_report_the_loss_and_the_recovery(dongle):
    hub = EdisioHub(port="/dev/ttyUSB0")
    changes = []
    hub.register_connection_callback(changes.append)
    await hub.connect()
    assert hub.connected

    dongle.unplug()
    assert not hub.connected
    dongle.replug()
    await wait_until(lambda: hub.connected)

    assert changes == [False, True]
    await hub.disconnect()


@pytest.mark.asyncio
async def test_disconnect_reports_no_connection_change(dongle):
    hub = EdisioHub(port="/dev/ttyUSB0")
    changes = []
    hub.register_connection_callback(changes.append)
    await hub.connect()

    await hub.disconnect()

    assert changes == []
    assert not hub.connected


@pytest.mark.asyncio
async def test_loss_and_recovery_are_logged_once(dongle, caplog):
    hub = EdisioHub(port="/dev/ttyUSB0")
    await hub.connect()

    with caplog.at_level("INFO", logger="custom_components.edisio.hub"):
        dongle.unplug()
        await wait_until(lambda: dongle.open_attempts >= 4)
        dongle.replug()
        await wait_until(lambda: hub.connected)
    await hub.disconnect()

    messages = [(r.levelname, r.getMessage()) for r in caplog.records
                if "/dev/ttyUSB0" in r.getMessage()]
    assert messages == [
        ("WARNING", "Lost serial port /dev/ttyUSB0, reconnecting: device disconnected"),
        ("INFO", "Reconnected to serial port /dev/ttyUSB0"),
    ]
