# Edisio

Home Assistant integration that turns Edisio radio wall switches into HA devices and button events, through a USB dongle.

## Language

**Dongle**:
The USB radio receiver connected to the HA host; the integration's single config entry.
_Avoid_: Gateway, hub, stick

**Device**:
A physical Edisio wall unit identified by its radio ID (e.g. `06708E57`); it appears as one HA device.
_Avoid_: Switch, interrupteur, board, transmitter

**Radio ID**:
The 8-hex-digit identifier a Device sends in every packet (e.g. `06708E57`); the byte-reversed hex of the decimal ID shown by RFPlayer.
_Avoid_: HA device ID (a different, HA-internal identifier), serial

**Button**:
One of the keys of a Device, identified by its Button number.
_Avoid_: Key, channel

**Button number**:
The two-digit radio code a Button sends, `01` to `08` (e.g. "Button 05"); the same value in events, entity names and automations.
_Avoid_: Button index, position, "Button 1..5"

**Button layout**:
How many Buttons a Device has active (1 to 5), which fixes the set of Button numbers it can send (e.g. 5 Buttons → `01 03 05 07 08`).
_Avoid_: Active buttons count, configuration

**Short press** / **Long press**:
The two kinds of press a Button reports to automations; one physical press yields exactly one of them.
_Avoid_: Click, hold, toggle, up/down
