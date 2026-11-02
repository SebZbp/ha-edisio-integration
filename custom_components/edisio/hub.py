import asyncio
import serial_asyncio_fast
from typing import Callable, Iterator, Optional, List, Dict, Any, Tuple
from .edisio_api import decode_packet

import binascii
import logging

_LOGGER = logging.getLogger(__name__)

_CLOSE_TIMEOUT = 5
_RECONNECT_MIN_DELAY = 1
_RECONNECT_MAX_DELAY = 60

def _reconnect_delays() -> Iterator[int]:
    """Seconds to wait before each attempt to reopen the port: 1, 2, 4... up to a minute."""
    delay = _RECONNECT_MIN_DELAY
    while True:
        yield delay
        delay = min(delay * 2, _RECONNECT_MAX_DELAY)

class EdisioProtocol(asyncio.Protocol):
    def __init__(
        self,
        packet_callback: Optional[Callable[[str], None]] = None,
        lost_callback: Optional[Callable[[Optional[Exception]], None]] = None,
    ) -> None:
        self.transport: Optional[asyncio.Transport] = None
        self.packet_callback: Optional[Callable[[str], None]] = packet_callback
        self.lost_callback: Optional[Callable[[Optional[Exception]], None]] = lost_callback
        self.buffer: bytes = b""
        self.closed = asyncio.Event()

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport # type: ignore
        _LOGGER.info("Edisio serial connection established")

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self.closed.set()
        if self.lost_callback:
            self.lost_callback(exc)

    def data_received(self, data: bytes) -> None:
        _LOGGER.debug("Raw data received: %s", binascii.hexlify(data).decode("ascii").upper())
        self.buffer += data
        while b"\x64\x0d\x0a" in self.buffer:
            packet, self.buffer = self.buffer.split(b"\x64\x0d\x0a", 1)
            full_packet = packet + b"\x64\x0d\x0a"
            
            if b"\x6c" in full_packet:
                full_packet = full_packet[full_packet.index(b"\x6c"):]
                packet_str: str = binascii.hexlify(full_packet).decode("ascii").upper()
                _LOGGER.info("Edisio Packet Extracted: %s", packet_str)
                if self.packet_callback:
                    self.packet_callback(packet_str)

class EdisioHub:
    def __init__(self, port: str) -> None:
        self.port: str = port
        self._transport: Optional[asyncio.Transport] = None
        self._protocol: Optional[EdisioProtocol] = None
        self.callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.connection_callbacks: List[Callable[[bool], None]] = []
        self._reconnect_task: Optional[asyncio.Task] = None
        self._stopping = asyncio.Event()

    @property
    def connected(self) -> bool:
        """Whether the serial port is open."""
        return self._transport is not None

    def register_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.callbacks.append(callback)

    def register_connection_callback(self, callback: Callable[[bool], None]) -> None:
        """Be told when the port is lost (False) or reopened (True); disconnect() is silent."""
        self.connection_callbacks.append(callback)

    def _handle_packet(self, packet_str: str) -> None:
        data: Dict[str, Any] = decode_packet(packet_str)
        if data:
            for cb in self.callbacks:
                cb(data)

    def _handle_connection_lost(self, exc: Optional[Exception]) -> None:
        if self._stopping.is_set():
            return
        self._transport = None
        self._protocol = None
        _LOGGER.warning("Lost serial port %s, reconnecting: %s", self.port, exc)
        self._notify_connection()
        self._reconnect_task = asyncio.get_running_loop().create_task(self._reconnect())

    def _notify_connection(self) -> None:
        for cb in self.connection_callbacks:
            cb(self.connected)

    async def _reconnect(self) -> None:
        for delay in _reconnect_delays():
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=delay)
                return
            except asyncio.TimeoutError:
                pass
            try:
                await self._open()
            except Exception as err:  # a half-enumerated USB device can raise termios.error too
                _LOGGER.debug("Serial port %s is not back yet: %s", self.port, err)
                continue
            _LOGGER.info("Reconnected to serial port %s", self.port)
            self._notify_connection()
            return

    async def connect(self) -> None:
        self._stopping.clear()
        await self._open()

    async def _open(self) -> None:
        loop = asyncio.get_running_loop()
        transport, protocol = await serial_asyncio_fast.create_serial_connection(
            loop,
            lambda: EdisioProtocol(self._handle_packet, self._handle_connection_lost),
            self.port,
            baudrate=9600,
        )
        self._transport = transport
        self._protocol = protocol

    async def disconnect(self) -> None:
        """Close the serial transport and drop callbacks so a reload starts clean."""
        self.callbacks.clear()
        self.connection_callbacks.clear()
        self._stopping.set()
        if self._reconnect_task is not None:
            # Awaited, not cancelled: an open running in the executor would leak the port.
            await self._reconnect_task
            self._reconnect_task = None
        transport, protocol = self._transport, self._protocol
        self._transport = None
        self._protocol = None
        if transport is None:
            return
        transport.close()
        if protocol is not None:
            try:
                await asyncio.wait_for(protocol.closed.wait(), timeout=_CLOSE_TIMEOUT)
            except asyncio.TimeoutError:
                _LOGGER.warning("Timed out waiting for serial port %s to close", self.port)
