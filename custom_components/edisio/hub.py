import asyncio
import serial_asyncio
from .edisio_api import decode_packet

class EdisioProtocol(asyncio.Protocol):
    def __init__(self, packet_callback=None):
        self.transport = None
        self.packet_callback = packet_callback
        self.buffer = b""

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        self.buffer += data
        while b"\r\n" in self.buffer:
            packet, self.buffer = self.buffer.split(b"\r\n", 1)
            packet_str = (packet + b"\r\n").decode("utf-8", errors="ignore").replace(" ", "")
            if self.packet_callback:
                self.packet_callback(packet_str)

class EdisioHub:
    def __init__(self, port: str):
        self.port = port
        self._transport = None
        self._protocol = None
        self.callbacks = []

    def register_callback(self, callback):
        self.callbacks.append(callback)

    def _handle_packet(self, packet_str: str):
        data = decode_packet(packet_str)
        if data:
            for cb in self.callbacks:
                cb(data)

    async def connect(self):
        loop = asyncio.get_running_loop()
        self._transport, self._protocol = await serial_asyncio.create_serial_connection(
            loop, lambda: EdisioProtocol(self._handle_packet), self.port, baudrate=9600
        )
