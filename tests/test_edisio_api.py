import pytest
from custom_components.edisio.edisio_api import is_valid_packet, decode_packet

def test_edisio_valid_packet():
    # A valid packet starts with 6C 76 63, ends with 64 0D 0A
    packet = "6C 76 63 00 00 00 00 00 01 0A 00 00 01 64 0D 0A"
    assert is_valid_packet(packet) is True

def test_edisio_invalid_packet():
    packet = "6C 76 63 00 00 00 00 00 01 0A 00 00 01 00 00 00"
    assert is_valid_packet(packet) is False

def test_decode_ebp8_short_press():
    # Example packet: PID=00000001, BID=01, MID=01, BL=2E (46 dec = ~139 battery), CMD=03 (toggle)
    packet = "6C 76 63 00 00 00 01 01 01 2E 00 00 03 64 0D 0A"
    result = decode_packet(packet)
    assert result["id"] == "00000001"
    assert result["button"] == "01"
    assert result["mid"] == "01"
    assert result["battery"] == "139" # int(46 / 3.3 * 10) = 139
    assert result["action"] == "toggle"

def test_decode_ebp8_long_press():
    # Long press for dimming usually sends CMD=07
    packet = "6C 76 63 00 00 00 01 01 01 2E 00 00 07 64 0D 0A"
    result = decode_packet(packet)
    assert result["button"] == "01"
    assert result["action"] == "up"
