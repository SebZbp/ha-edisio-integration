# Blueprint: match real Button numbers 01–08

Tracker: beads epic `edisio-p7j` (label `ready-for-agent`)

## Problem Statement

The blueprint `blueprints/automation/edisio/ebp8b_controller.yaml` offers "Button 1" to "Button 5" and compares the event's `button` against `'01'` to `'05'`. The Button numbers a Device actually sends depend on its Button layout (5 Buttons → `01 03 05 07 08`, 4 → `01 03 07 08`, 3 → `02 07 08`, 2 → `04 06`, 1 → `05`), so presses on Buttons `06`, `07` and `08` never match, and on a 5-Button Device "Button 2" (`02`) is never sent at all. The Device is also chosen by typing its Radio ID as free text: a typo silently matches nothing.

## Solution

The blueprint has one short-press and one long-press action per Button number `01` to `08`, grouped in a collapsible section per Button, each describing which Button layouts include it. The Device is picked with an HA device selector restricted to the Edisio integration; the blueprint derives the Radio ID from the selected device and matches it against the event.

## User Stories

1. As an automation author, I want an action input for every Button number a Device can send (`01`–`08`), so that every physical Button can be automated.
2. As an automation author, I want separate short-press and long-press actions per Button, so that I can map both like in my RFPlayer automations.
3. As an automation author, I want each Button's inputs labelled "Button 05" and grouped in a collapsible section, so that the form stays readable with 16 inputs.
4. As an automation author, I want each section to say which Button layouts include that Button, so that I know which ones apply to my Device.
5. As an automation author, I want to pick the Device from a list of Edisio devices ("BP Cuisine") instead of typing its Radio ID, so that I cannot mistype it.
6. As an automation author, I want unused Buttons left empty to do nothing, so that I only fill what my Device has.
7. As an automation author, I want the blueprint to rely only on the unchanged `edisio_button_event` payload, so that it keeps working across plugin versions.

## Implementation Decisions

- Inputs: for each Button number `01`–`08`, an input section "Button <n>" (collapsed by default) holding `button_<n>_short` and `button_<n>_long` action selectors, default empty. Section descriptions list the layouts that contain the Button (from `BUTTON_CONFIGS`).
- Device input: device selector with `integration: edisio`. The Radio ID is the second element of the device's `(edisio, <Radio ID>)` identifier, read with a template. Because trigger `event_data` cannot use a full template, the trigger listens to all `edisio_button_event` events and a condition compares `trigger.event.data.device_id` to the derived Radio ID.
- Actions: a `choose` with one branch per Button number and press type, comparing `button` to the two-digit Button number and `type` to `short_press` / `long_press`.
- The blueprint requires an HA version that supports blueprint input sections; the `homeassistant: min_version` key is set accordingly.
- Blueprint mode: `queued` so quick successive presses are not dropped.
- Existing automations created from the old blueprint are not migrated (the blueprint is alpha; the README says so). Input keys `button_1_*` .. `button_5_*` are replaced by `button_01_*` .. `button_08_*`.
- README blueprint section updated (Button numbers per layout, device selector).
- ADRs: none exist; no contradiction.

## Testing Decisions

- The blueprint is YAML, not Python: a test loads it, checks it parses with HA's blueprint schema, and asserts that the set of Button numbers it handles equals the union of all Button numbers in `BUTTON_CONFIGS`, so the blueprint and the layouts cannot drift apart again.
- Manual check on the live installation: create an automation from the blueprint for BP Bas escalier (`06709603`), bind a notification to Button `07` short press, press it, see the notification.
- Prior art: none for blueprints; test style as in `tests/`.

## Out of Scope

- Per-layout blueprints.
- Migration of automations made from the old blueprint.
- Hold-to-dim or repeat behaviour (see `long-press-decoding.md`).
- Any change to `edisio_button_event`.

## Further Notes

- Depends on `edisio-b0a` (Button numbers as the shared naming).
- Domain terms are defined in `CONTEXT.md`.
