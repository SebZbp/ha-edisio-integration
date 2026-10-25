"""USB discovery must only offer the Edisio dongle, never the RFPlayer (edisio-vdm)."""
import json
from pathlib import Path

MANIFEST = Path(__file__).parent.parent / "custom_components" / "edisio" / "manifest.json"


def test_usb_matchers_exclude_rfplayer_ftdi_chip():
    matchers = json.loads(MANIFEST.read_text())["usb"]
    assert {(m["vid"], m["pid"]) for m in matchers} == {("067B", "2303")}
