import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from custom_components.edisio.hub import EdisioHub, EdisioProtocol

@pytest.mark.asyncio
async def test_edisio_hub_connect():
    hub = EdisioHub(port="/dev/ttyUSB0")
    
    with patch("serial_asyncio.create_serial_connection") as mock_create_connection:
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
    protocol.data_received(b"6C 76 63 00 00 00 ")
    callback.assert_not_called()
    
    # Complete the packet
    protocol.data_received(b"01 01 01 2E 00 00 03 64 \r\n")
    callback.assert_called_once_with("6C76630000000101012E00000364\r\n")
    
    # Send multiple packets at once
    callback.reset_mock()
    protocol.data_received(b"6C 76 63 00 00 00 01 01 01 2E 00 00 03 64 \r\n6C 76 63 00")
    callback.assert_called_once_with("6C76630000000101012E00000364\r\n")
