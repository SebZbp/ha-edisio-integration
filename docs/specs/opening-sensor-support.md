# Opening sensor support

Tracker: beads epic `edisio-voy` (label `ready-for-agent`, blocked on the overnight log check `edisio-avx`)

## Problem Statement

The integration only understands Wall plates. A home owner with an Edisio Opening sensor (EDS-100, requested in GitHub issue #8) cannot see whether a door or window is Open or Closed in Home Assistant. Worse, the sensor sends Button number `01`, so it is offered as an EBP8 today: the discovery card asks for a Button layout, and once configured every door movement fires `edisio_button_event`.

## Solution

An Opening sensor is recognised from the Model code in its packets. Its discovery card asks only for a name and an area. It then appears as one HA device with an Open/Closed sensor and a battery level, both of which survive a restart. It can also be added by hand. Wall plates keep working exactly as they do today.

The EDS-100 is the tested product. The EOS-200 is expected to send the same Model code, so it should work the same way, but it is untested and documented as such.

## User Stories

1. As a home owner, I want an Opening sensor to be recognised automatically, so that I do not have to know its Model code.
2. As a home owner, I want moving the magnet to raise a discovery card, so that adding a sensor works like adding a Wall plate.
3. As a home owner, I want pressing the Sensor button to raise the same discovery card, so that I can add a sensor without opening a door.
4. As a home owner, I want the card to show the Radio ID and say it is an Opening sensor, so that I know what I am configuring.
5. As a home owner, I want the card to ask only for a name and an area, so that I am not asked about Buttons a sensor does not have.
6. As a home owner, I want a useful default name when I leave the name empty, so that the HA device is never nameless.
7. As a home owner, I want no second card for a sensor that already has one in progress, so that I am not flooded while testing a door.
8. As a home owner, I want to see Open or Closed for each sensor, so that I know the state of my doors and windows.
9. As a home owner, I want the state to change as soon as the door moves, so that I can trust what HA shows.
10. As a home owner, I want a battery level for each sensor, so that I can replace an old battery before it dies.
11. As a home owner, I want the Sensor button to update the battery level and change nothing else, so that testing a sensor does not report a false door movement.
12. As a home owner, I want to show the sensor as a door or a window using HA's "Show as" setting, so that the icon and wording match what it is mounted on.
13. As a home owner, I want the last known state and battery level back after a restart, so that I do not see "unknown" until the door next moves.
14. As a home owner, I want "unknown" only for a sensor that has never reported, so that HA does not invent a state.
15. As a home owner, I want to add a sensor by typing its Radio ID and choosing its model, so that I can configure it from my desk.
16. As a home owner, I want to edit a sensor's name and area, so that I can change them later.
17. As a home owner, I want no Button layout on a sensor's edit form, so that the form only shows what applies.
18. As a home owner, I want "Also update entity IDs" to work for a sensor, so that all its entities follow its new name.
19. As a home owner, I want to remove a sensor like any other Device, so that it is forgotten and offered again if it transmits.
20. As a home owner with Wall plates, I want them to keep their entities, events, names and blueprints, so that upgrading breaks nothing.
21. As an automation author, I want to trigger on the sensor's state, so that I can use HA's standard door automations.
22. As an automation author, I want no `edisio_button_event` from a sensor, so that a door movement never looks like a Button press.
23. As a blueprint user, I want sensors left out of the Wall plate blueprint's Device selector, so that I cannot pick a Device with no Buttons.
24. As an EOS-200 owner, I want the sensor treated the same way, so that it may work without a code change.
25. As an EOS-200 owner, I want the docs to say it is untested, so that I know what to expect and can report problems.
26. As a neighbour of another Edisio installation, I want a foreign sensor to be only an ignorable card, so that nothing is added without my action.
27. As a maintainer, I want decoding backed by recorded frames from a real sensor, so that it is not guesswork.
28. As a maintainer, I want one place that defines what each Device model reports, so that adding a Device model later does not touch discovery.
29. As a French-speaking user, I want new text to be translatable, so that the card reads naturally in my language.
30. As a maintainer, I want the vocabulary of `CONTEXT.md` used in the UI and the docs, so that users and docs share the same language.

## Implementation Decisions

### Recorded behaviour

Recorded on 2026-10-31 from one EDS-100, Radio ID `91107A5D`, with a new battery. The frame format is the same 16 bytes as a Wall plate.

| Field | Value |
| --- | --- |
| Model code | `09` (all 15 Wall plates in the same installation send `01`) |
| Button number field | Always `01`; it carries no meaning for an Opening sensor |
| Closed (magnet against the sensor) | Commands `01` then `09` |
| Open (magnet away from the sensor) | Commands `02` then `0A` |
| Sensor button | Command `2F` |

- Every transition delivered both of its commands, as bursts of 2 to 5 frames. Frames within a burst can be lost.
- The owner found no way to change polarity on the device, and the mapping above was confirmed against the magnet's real position.

### Device model

- A single table maps a Model code to a Device model and defines what that model reports. It holds Wall plate (`01`) and Opening sensor (`09`). Adding a Device model later means adding an entry, plus its entities if they are new.
- The Device model is stored per Device in the integration's options. A stored Device with no model is a Wall plate, so no migration is needed.
- The stored model is the truth for a configured Device; packets do not change it. A sensor already configured as a Wall plate must be removed and discovered again. Changing a Device's model on the edit form is not offered.
- The Model code does not encode the Button layout: 2-, 3- and 5-Button Wall plates all send `01`. The Button layout stays a user choice.

### Packet handling

- Packet routing follows the stored Device model. Only a Wall plate fires `edisio_button_event` and updates Button sensors.
- Either command of a pair sets the state, so a lost frame cannot lose a transition.
- `2F` and any other command from an Opening sensor update the battery only.
- Packets still pass through the existing repeat filter. Writing the same state twice is harmless, so the two commands of a pair need no special handling.

### Discovery

- Any packet with Model code `09` from an unconfigured Radio ID raises an Opening sensor card, including the Sensor button.
- Any other Model code keeps today's behaviour: Button numbers `01` to `08` raise a Wall plate card and anything else is ignored. Other installations may have plates that send `02` to `05`, so discovery is not restricted to the table.
- The flow receives the Model code. The existing one-card-per-Radio-ID guard is unchanged.
- The Opening sensor card has an optional name and area and no Button layout.

### Home Assistant representation

- An Opening sensor is one HA device, linked to the Dongle, with a `binary_sensor` of class `opening` and the Battery sensor. It has no Button sensors. On means Open.
- Users set door or window through HA's own "Show as" option, so there is no integration setting for it.
- The default name is "Edisio Opening sensor <Radio ID>" and the device model is "Opening sensor", because the Model code cannot tell an EDS-100 from an EOS-200.
- Wall plates keep model "EBP8" and their default name. This keeps sensors out of the blueprint's Device selector, which filters on that model.
- The integration gains the `binary_sensor` platform.

### Restart behaviour

- The Open/Closed state and the Battery level are restored after a restart. Battery restore applies to every Device, including Wall plates.
- A state stays unknown only until the first report. A transition missed while HA was down shows the old state until the next transition; this limit is documented.

### Options flow

- The Add form gains a Device model choice. The Button layout is asked only for a Wall plate.
- The edit form hides the Button layout for an Opening sensor.
- The entity ID update must use each entity's own domain. It currently assumes `sensor`, which would produce a wrong target for the `binary_sensor`.

### To be decided from the overnight log (`edisio-avx`)

- Whether the sensor sends a heartbeat. If it does not, there is no availability or staleness handling, and the entity relies on restore alone.
- If it does, whether its frames carry the state, and whether they should feed a stale or unavailable state. Close this section in this spec either way.

## Testing Decisions

- Good tests assert externally visible behaviour: entity states, events fired, forms shown, stored options, registry entries. They do not assert private helpers or the table's shape.
- Primary seam: the existing packet-to-event path. Tests feed recorded frames, as hex strings, into the running integration and assert entity states and events. Use the frames captured from `91107A5D`, including a burst with a lost frame and the `2F` frame.
- Secondary seams, all existing: the configuration flow for the discovery card, the options flow for Add and edit, and device registration for names and models. No new seam is needed.
- Wall plate regression: replaying the recorded Wall plate frames still fires the same events, and existing Devices keep their entities.
- Restart: a restored state and Battery level appear after setup, and a sensor with no history stays unknown.
- Prior art: the replay tests for one event per press, the discovery tests for unknown Devices, and the options flow tests. The test that pins `70051C01` as ignored stays valid.

## Out of Scope

- Controlling the EMV-400, EMSD-300 or any other receiver. The integration stays receive-only; this would need transmit, pairing and new entity types.
- Temperature, motion and other Device models. The table makes them possible, but none is built here.
- A per-Device polarity or NO/NF invert option. The EDS-100 offers no way to change it. Revisit if an EOS-200 report shows reversed states.
- Tamper reporting on the EOS-200, which is unobserved.
- Identifying what `70051C01` is.
- Telling an EDS-100 from an EOS-200.
- Changing the `edisio_button_event` payload.
- Automatically converting a sensor already configured as a Wall plate.

## Further Notes

- The Jeedom plugin's model `09` is the source for the EOS-200 expectation. Its definition uses the EOS-200's battery and documentation. It is GPL-2.0, so use it for protocol facts only and copy no code.
- The catalogue says the EDS-100's signal is configurable as NO or NF and contradicts itself on whether closing is reported. The recorded behaviour above takes precedence.
- The byte after the battery is `05` on the sensor and `01` on plates. Its meaning is unknown and nothing depends on it.
- HA currently runs a `[DEBUG-1h5]` diagnostic build. Keep it until the overnight check is done, and do not submit the pending card for `91107A5D`; submitting it would store the sensor as a Wall plate.
- Domain terms are defined in `CONTEXT.md`.
