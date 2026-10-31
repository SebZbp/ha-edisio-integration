# Edisio

Home Assistant integration that turns Edisio radio wall plates and opening sensors into HA devices, button events and open/closed states, through a USB dongle.

## Language

**Dongle**:
The USB radio receiver connected to the HA host; the integration's single config entry.
_Avoid_: Gateway, hub, stick

**Device**:
A physical Edisio unit that sends radio packets, identified by its Radio ID (e.g. `06708E57`); it appears as one HA device.
_Avoid_: Switch, interrupteur, board, transmitter

**Device model**:
The kind of a Device, which decides what it reports: a Wall plate or an Opening sensor. It is known from the Model code, or chosen when a Device is added by hand.
_Avoid_: Type, product

**Model code**:
The two-digit code a Device sends in every packet to say which kind of Device it is (e.g. `01`, `09`). It names a kind, not an exact product: EDS-100 and EOS-200 are not told apart.
_Avoid_: mid

**Wall plate**:
A Device with Buttons, such as an EBP8. Every Wall plate seen so far sends Model code `01`, whatever its Button layout.
_Avoid_: Plate base, switch, EBP8 (a product name, not a kind)

**Opening sensor**:
A Device with a magnet that reports whether a door or window is Open or Closed, such as an EDS-100. It sends Model code `09`.
_Avoid_: Detector, contact, door sensor, window sensor

**Open** / **Closed**:
The two states of an Opening sensor: Open when the magnet is away from the sensor, Closed when it is against it.
_Avoid_: On/off, triggered

**Sensor button**:
The single push button on an Opening sensor. It changes no state and is not a Button: it has no Button number and no presses.
_Avoid_: Button, pairing button (its purpose is unconfirmed)

**Radio ID**:
The 8-hex-digit identifier a Device sends in every packet (e.g. `06708E57`); the byte-reversed hex of the decimal ID shown by RFPlayer.
_Avoid_: HA device ID (a different, HA-internal identifier), serial

**Button**:
One of the keys of a Wall plate, identified by its Button number.
_Avoid_: Key, channel

**Button number**:
The two-digit radio code a Button sends, `01` to `08` (e.g. "Button 05"); the same value in events, entity names and automations.
_Avoid_: Button index, position, "Button 1..5"

**Button layout**:
How many Buttons a Wall plate has active (1 to 5), which fixes the set of Button numbers it can send (e.g. 5 Buttons → `01 03 05 07 08`).
_Avoid_: Active buttons count, configuration

**Short press** / **Long press**:
The two kinds of press a Button reports to automations; one physical press yields exactly one of them.
_Avoid_: Click, hold, toggle, up/down
