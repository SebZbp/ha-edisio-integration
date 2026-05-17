import pytest
from custom_components.edisio.edisio_api import is_valid_packet, decode_packet

def test_edisio_valid_packet():
    # A valid packet starts with 6C 76 63, ends with 64 0D 0A
    packet = "6C 76 63 00 00 00 00 00 01 0A 00 00 01 64 0D 0A"
    assert is_valid_packet(packet) is True

def test_edisio_invalid_packet():
    packet = "6C 76 63 00 00 00 00 00 01 0A 00 00 01 00 00 00"
    assert is_valid_packet(packet) is False
