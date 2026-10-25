# Stable Button naming by Button number

Tracker: beads epic `edisio-b0a` (label `ready-for-agent`)

## Problem Statement

Button sensors are named after their position in the Button layout ("Button 1", "Button 2", ...), not after the Button number the Device actually sends. On a 5-Button Device the sensor called "Button 2" receives Button `03`, while `edisio_button_event` reports `button: "03"`, so names, events and automations disagree. Because HA freezes entity IDs at first registration, Devices registered by different plugin versions also ended up with inconsistent entity IDs: on `04997264`, `sensor.edisio_ebp8_b_04997264_button_2` has unique ID `04997264_button_03`, while on `06708DE5`, `sensor.edisio_ebp8_b_06708de5_button_3` has unique ID `06708DE5_button_03`.

## Solution

Each Button sensor is named "Button <Button number>" (e.g. "Button 05"), the same two-digit value carried in `edisio_button_event` and used by the blueprint. Unique IDs stay `<Radio ID>_button_<Button number>`, unchanged. Existing entity IDs are not migrated automatically; they become consistent when the user renames a Device in the options flow with "also update entity IDs" checked (`options-flow-device-management.md`).

## User Stories

1. As a home owner, I want each Button sensor named after its Button number ("Button 05"), so that the name matches what the Device sends.
2. As an automation author, I want the sensor name, the `button` field of `edisio_button_event` and the blueprint to use the same Button number, so that I never have to translate between them.
3. As a home owner, I want the same Button number to give the same sensor name on every Device with the same Button layout, so that Devices are consistent.
4. As a home owner, I want existing sensors to keep their unique ID, history and customisations, so that upgrading loses nothing.
5. As a home owner, I want existing entity IDs left alone on upgrade, so that dashboards or scripts using them keep working.
6. As a home owner, I want a way to make entity IDs consistent when I choose to, so that the `button_2` / `button_03` mismatch can be fixed (via the options flow rename).
7. As a home owner, I want newly created Button sensors to get entity IDs ending in `_button_<Button number>`, so that new Devices are consistent from the start.
8. As a maintainer, I want the glossary term "Button number" used in code and UI, so that "index" and "position" disappear.

## Implementation Decisions

- A Button sensor's display name is "Button " followed by the two-digit Button number from the Button layout (`BUTTON_LAYOUTS`), e.g. "Button 01", "Button 07". The sequential index is no longer used for naming.
- Unique IDs remain `<Radio ID>_button_<Button number>`; nothing in the registry is rewritten on upgrade.
- Because the name of an existing entity changes but its entity ID is frozen, existing entities show the new name with their old entity ID until the user opts into the options-flow entity ID update. New entities get entity IDs derived from "<device name> Button <Button number>", i.e. ending in `_button_<Button number>`.
- Sensor state values ("normal", "short-press", "long-press") are unchanged.
- `edisio_button_event` is unchanged.
- The README section on Button naming is updated to describe Button numbers per layout.
- ADRs: none exist; no contradiction.

## Testing Decisions

- Tests assert entity names, unique IDs and entity IDs as seen in the entity registry; no private helpers.
- For each Button layout (1 to 5), the created Button sensors are named "Button <n>" for exactly the Button numbers of that layout, with unique IDs `<Radio ID>_button_<n>`.
- Upgrade scenario: an entity registry pre-seeded with `sensor.edisio_ebp8_b_04997264_button_2` / unique ID `04997264_button_03` keeps that entity ID after setup, and its name becomes "Button 03".
- A brand-new Device gets entity IDs ending in `_button_<Button number>`.
- Prior art: `tests/test_sensor.py`.

## Out of Scope

- Automatic migration of existing entity IDs (decided against; opt-in via the options flow).
- Per-Button custom names.
- Position-based names ("top left", ...).
- Changes to sensor states or to `edisio_button_event`.

## Further Notes

- The options flow's "also update entity IDs" relies on this naming (`edisio-zmz`), and the blueprint aligns with it (`edisio-p7j`).
- Domain terms are defined in `CONTEXT.md`.
