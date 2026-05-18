import asyncio
import serial_asyncio_fast
from typing import Callable, Optional, List, Dict, Any, Tuple
from .edisio_api import decode_packet

import binascii
import logging

_LOGGER = logging.getLogger(__name__)

class EdisioProtocol(asyncio.Protocol):
    def __init__(self, packet_callback: Optional[Callable[[str], None]] = None) -> None:
        self.transport: Optional[asyncio.Transport] = None
        self.packet_callback: Optional[Callable[[str], None]] = packet_callback
        self.buffer: bytes = b""

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport # type: ignore
        _LOGGER.info("Edisio serial connection established")

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

    def register_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.callbacks.append(callback)

    def _handle_packet(self, packet_str: str) -> None:
        data: Dict[str, Any] = decode_packet(packet_str)
        if data:
            for cb in self.callbacks:
                cb(data)

    async def connect(self) -> None:
        loop = asyncio.get_running_loop()
        transport, protocol = await serial_asyncio_fast.create_serial_connection(
            loop, lambda: EdisioProtocol(self._handle_packet), self.port, baudrate=9600
        )
        self._transport = transport
        self._protocol = protocol
