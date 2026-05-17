import asyncio
import serial_asyncio
from typing import Callable, Optional, List, Dict, Any, Tuple
from .edisio_api import decode_packet

class EdisioProtocol(asyncio.Protocol):
    def __init__(self, packet_callback: Optional[Callable[[str], None]] = None) -> None:
        self.transport: Optional[asyncio.Transport] = None
        self.packet_callback: Optional[Callable[[str], None]] = packet_callback
        self.buffer: bytes = b""

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport # type: ignore

    def data_received(self, data: bytes) -> None:
        self.buffer += data
        while b"\r\n" in self.buffer:
            packet, self.buffer = self.buffer.split(b"\r\n", 1)
            packet_str: str = (packet + b"\r\n").decode("utf-8", errors="ignore").replace(" ", "")
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
        transport, protocol = await serial_asyncio.create_serial_connection(
            loop, lambda: EdisioProtocol(self._handle_packet), self.port, baudrate=9600
        )
        self._transport = transport
        self._protocol = protocol
