# Options flow: manage Devices from Configure

Tracker: beads epic `edisio-zmz` (label `ready-for-agent`)

## Problem Statement

Once a Device is configured through its discovery card, nothing about it can be changed from the integration: its Button layout is fixed for good (a wrong answer means deleting the integration), and the only way to add a Device is to walk to it and press a Button, then answer a card. The home owner has 15 Devices whose Radio IDs are already known (from the former RFPlayer setup) and wants to enter them from a desk. Packets from Devices that are not configured do not even fire `edisio_button_event`, so automations cannot be migrated until every Device is configured.

## Solution

The integration's "Configure" button opens an options flow with a menu:

- **Add a Device**: Radio ID, optional name, optional area, Button layout. The Device is configured immediately, without pressing it.
- **Edit a Device**: pick a configured Device, then change its name (with an "also update entity IDs" option), its area and its Button layout.
- **Remove a Device**: pick a configured Device and forget it.

## User Stories

1. As a home owner, I want to add a Device by typing its Radio ID, so that I can configure all my Devices from a desk without pressing each one.
2. As a home owner, I want the Radio ID to be accepted in any case and stored in uppercase, so that "0670a248" and "0670A248" are the same Device.
3. As a home owner, I want a malformed Radio ID (not exactly 8 hex digits) to be rejected with a clear error, so that I do not create a Device that will never receive anything.
4. As a home owner, I want a Radio ID that is already configured to be rejected, so that I cannot create duplicates.
5. As a home owner, I want to give the new Device a name ("BP Cuisine") and an area (Cuisine) in the same form, so that it is ready in one step.
6. As a home owner, I want to choose the Button layout (1 to 5 active Buttons) when adding a Device, so that the right Button sensors are created.
7. As a home owner, I want a manually added Device to appear immediately with its sensors (battery unknown until the first packet), so that I can use it in automations before ever pressing it.
8. As a home owner, I want a manually added Device's Buttons to fire `edisio_button_event` as soon as they are pressed, so that it behaves exactly like a discovered Device.
9. As a home owner, I want a pending discovery card for a Device I just added manually to disappear, so that I am not asked to configure it twice.
10. As a home owner, I want to rename a configured Device from the options flow, so that I can apply my "BP <room>" convention to Devices that were configured before naming existed.
11. As a home owner, I want the name I type in the options flow to be the name I see, even if I renamed the Device on HA's device page earlier, so that there is one obvious place where the name is set.
12. As a home owner, I want an option to also update the Device's entity IDs when I rename it, so that entity IDs follow the new name and become consistent across Devices.
13. As a home owner, I want the entity ID update to be opt-in, so that dashboards or scripts that use the old IDs do not break unless I ask.
14. As a home owner, I want to change the area of a configured Device from the options flow, so that I can place all my Devices from one screen.
15. As a home owner, I want to change the Button layout of a configured Device, so that a wrong answer at setup can be fixed without deleting the integration.
16. As a home owner, I want sensors for Button numbers that no longer exist in the new layout to be removed, so that I am not left with dead entities.
17. As a home owner, I want sensors for Button numbers present in both layouts to keep their entity, history and unique ID, so that nothing that still applies is lost.
18. As a home owner, I want to remove a Device, so that a switch I took out of the wall no longer clutters HA.
19. As a home owner, I want a removed Device to be offered again through a discovery card if it is ever pressed again, so that removal is reversible.
20. As an automation author, I want `edisio_button_event` payloads to be unchanged by any of these operations, so that my automations keep working.
21. As a French-speaking user, I want the options flow text to be translatable, so that it reads naturally in my language.
22. As a maintainer, I want the options flow to use the terms Dongle, Device, Radio ID, Button and Button layout from `CONTEXT.md`, so that UI and docs share one language.

## Implementation Decisions

- The Dongle config entry gets an options flow (menu step) with three branches: add, edit, remove. Each branch ends by writing the entry's options; the existing update listener reloads the entry, which (re)creates the Device's entities.
- Stored per-Device configuration (in the entry options, keyed by Radio ID) remains: Button layout and, optionally, name. No area and no entity IDs are stored there. The data shape is shared with the discovery card (`device-identification-at-discovery.md`, epic `edisio-2n1`), which defines the name field, the empty-name rule and the default name "Edisio EBP8-B <Radio ID>".
- **Add**: Radio ID is normalised (trimmed, uppercased) and validated as exactly 8 hex digits; an already configured Radio ID is an error on the form, not an abort. Name and area are optional; Button layout defaults to 5. The area is applied to the registry entry once it exists (same rule as the discovery card). Any in-progress discovery flow for the same Radio ID is aborted. The field description gives the format hint "8 hex digits, e.g. 0670A248"; RFPlayer decimal IDs are not accepted.
- **Edit, name**: the new name is stored in the options and the registry's `name_by_user` for that Device is cleared, so the typed name is the visible one. An empty name removes the stored name (default name applies).
- **Edit, entity IDs**: an optional checkbox "also update entity IDs" (default off). When on, every entity of the Device gets the entity ID `sensor.<slug of device name>_battery` or `sensor.<slug of device name>_button_<Button number>` (Button number per `stable-button-naming.md`), skipping any whose target ID is already taken by another entity (reported, not overwritten). Unique IDs never change.
- **Edit, area**: shown pre-filled with the registry's current area; the submitted value is written to the device registry directly.
- **Edit, Button layout**: on change, entities whose unique ID refers to a Button number that is not in the new layout are removed from the entity registry; entities for Button numbers present in both layouts are untouched.
- **Remove**: the Device is deleted from the options, and its device and entities are removed from the registries. A later packet from it starts a discovery flow as for any unknown Device. HA's native "Delete" on the device page (`async_remove_config_entry_device`) may share this logic; it is not required here.
- The menu's edit and remove branches list configured Devices by display name and Radio ID ("BP Cuisine (06708E57)").
- UI strings live in `strings.json` / translations under `options`.
- ADRs: none exist; no contradiction.

## Testing Decisions

- Tests assert externally visible behaviour only: options content after each branch, device registry (name, `name_by_user`, area), entity registry (entity IDs, unique IDs, removed entities), form errors, flows in progress. No private helpers.
- Primary seam: the options flow, driven through HA's flow manager on a configured Dongle entry.
  - Add: valid lowercase ID is stored uppercase with layout and name; invalid ID and duplicate ID return form errors; area ends up on the registry entry; a pending discovery flow for that ID is gone.
  - Edit: rename stores the name and clears `name_by_user`; checkbox on rewrites entity IDs to the expected pattern while unique IDs stay; checkbox off leaves entity IDs; area change lands in the registry; layout 5 → 3 removes Button `01`, `03`, `05` entities, keeps `07`, `08` (same unique ID) and adds `02`.
  - Remove: Device gone from options and registries; a subsequent packet from it starts a discovery flow.
- Secondary seam, event handling: a packet from a manually added Device that was never pressed fires `edisio_button_event` with the unchanged payload.
- Prior art: existing config flow tests (`tests/test_config_flow.py`) and sensor/registry tests (`tests/test_sensor.py`, `tests/test_init.py`).

## Out of Scope

- Choosing the Device model (backlog issue; model stays "EBP8-B").
- Accepting RFPlayer decimal IDs.
- Per-Button names or per-Button enable/disable beyond the Button layout.
- Changing the serial port of the Dongle (backlog issue on by-id paths).
- Bulk import (CSV/YAML) of Devices.
- Any change to the `edisio_button_event` payload.

## Further Notes

- Depends on `edisio-2n1` (name and area fields, default name) and on `edisio-b0a` (Button number naming used by the entity ID pattern).
- The user's 11 Devices still to add are listed in the migration notes of the HA config work, not here; this spec only provides the means.
- Domain terms are defined in `CONTEXT.md`.
