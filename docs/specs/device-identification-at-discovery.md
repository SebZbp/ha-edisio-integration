# Device identification at discovery

Tracker: beads epic `edisio-2n1` (label `ready-for-agent`)

## Problem Statement

When a new Device is detected, Home Assistant shows a card "Configure Edisio Device 06708E57". The only identifier is a Radio ID such as `06708E57`, which means nothing to the user. With a dozen wall switches in a house, the user cannot tell which physical Device the card refers to, and ends up with unnamed HA devices that are hard to tell apart and that sit in no area.

## Solution

When the discovery card appears, it tells the user which Device and which Button triggered it ("Button 05 was pressed on Device 06708E57"), so the user can match the card to the physical switch they just pressed. The card also offers an optional name field (house convention: "BP <room>", e.g. "BP Cuisine") and an optional HA area, so the HA device is named and placed in one step. If the name is left empty, the existing default name "Edisio EBP8-B <Radio ID>" is used, so already configured Devices are not renamed.

## User Stories

1. As a home owner, I want the discovery card to show the Device's Radio ID, so that I can recognise the Device later in logs and the HA device list.
2. As a home owner, I want the discovery card to show which Button was pressed, so that I can confirm the card matches the switch I just pressed.
3. As a home owner, I want the card to show the Button whose press started the discovery, so that I can tell which physical Device it is even if I pressed other Buttons on it afterwards.
4. As a home owner, I want to type a name for the Device on the card, so that its HA device is called "BP Cuisine" instead of an ID.
5. As a home owner, I want the name field to be optional, so that I can finish configuration quickly and rename later.
6. As a home owner, I want the existing default name when I leave the field empty, so that the HA device is never nameless and naming stays consistent with Devices configured earlier.
7. As a home owner, I want to pick the HA area of the Device on the same card, so that the Device is named and placed in one step.
8. As a home owner, I want the area field to be optional, so that I can place the Device later from HA's device page.
9. As a home owner, I want the Button layout question (1 to 5 active Buttons) to remain on the same card, so that configuration stays a single step.
10. As a home owner, I want the chosen name to be used by the Device's sensors (battery, Buttons), so that every entity of the Device is recognisable.
11. As a home owner, I want the name to persist across HA restarts and integration reloads, so that I do not have to re-enter it.
12. As a home owner, I want the Device to remain linked to the Dongle in the device registry, so that the existing hierarchy is unchanged.
13. As a home owner, I want an already configured Device to keep its current name and behaviour, so that upgrading the integration does not break anything.
14. As a home owner, I want no second discovery card for a Device that already has one in progress, so that I am not flooded while pressing Buttons.
15. As an automation author, I want `edisio_button_event` payloads to be unchanged, so that my existing automations keep working.
16. As a French-speaking user, I want the new text to be translatable, so that the card reads naturally in my language.
17. As a maintainer, I want the vocabulary Dongle / Device / Button used consistently in UI text, so that users and docs share the same language.

## Implementation Decisions

- The discovery flow receives the Button number in addition to the Radio ID; the received packet already carries it. The event path that starts the flow passes it along.
- The discovery card shows the Radio ID and the Button number through description placeholders; no other identification mechanism (blinking, test action) is added.
- The card shows the Button of the press that started the flow. Later presses on the same Device do not touch the in-progress flow: HA stores a shown form as a static result, so updating it would mean aborting and restarting the flow, which could discard a card the user is filling in. (Resolves the former conflict between "last Button pressed" and "no second card".)
- The configuration form gains two optional fields next to the Button layout (1 to 5, unchanged): a text field "name" and an HA area selector.
- On submit, the Device's stored configuration holds the Button layout and, when provided, the name. An empty or whitespace-only name is treated as not provided and is not stored.
- The area is not stored in the integration's options. It is applied to the Device's entry in the device registry once, when that entry is created; afterwards the device registry (HA device page or the options flow, see `options-flow-device-management.md`) is the only source of truth for the area.
- The HA device name is the stored name, falling back to "Edisio EBP8-B <Radio ID>" when absent (the current default in the code, kept so existing Devices are not renamed). Manufacturer ("Edisio") and model stay in their own device-info fields; the location lives in the HA area, not in the name.
- Devices configured before this change have no stored name and keep the fallback name; no migration is required. A name the user set on HA's device page (`name_by_user`) keeps taking precedence, as HA does natively.
- Unique-id handling and the "flow already in progress" guard are unchanged: one card per Device, identified by the Radio ID.
- UI strings (English source and translations) use the terms Dongle, Device, Button and Button layout as defined in `CONTEXT.md`.
- ADRs: none exist; no contradiction.

## Testing Decisions

- Good tests only assert externally visible behaviour: form content, stored options, registered device name and area, flow-start arguments. They do not assert private helpers.
- Primary seam: the configuration flow. Calling the discovery step with a Radio ID and a Button number yields a form whose placeholders contain both; submitting with a name stores it with the Button layout; submitting without a name (or with blanks) stores no name and the fallback name applies; submitting with an area stores no area in options.
- Secondary seam, event handling: when a packet from an unknown Device arrives, the flow is started with both the Radio ID and the Button number; a second packet from the same Device while the flow is in progress starts no flow and leaves the first flow's placeholders unchanged.
- Secondary seam, device registry: a configured Device with a stored name is registered under that name; one without is registered under "Edisio EBP8-B <Radio ID>"; a Device configured with an area has that area on its registry entry after setup.
- Prior art: the existing tests for the config flow device steps, for the unknown-Device flow start, and for sensor/device registration.

## Out of Scope

- Renaming, re-placing or changing the Button layout of a Device after configuration, adding a Device without pressing it, and removing a Device: see `options-flow-device-management.md` (epic `edisio-zmz`).
- Button sensor names: see `stable-button-naming.md` (epic `edisio-b0a`).
- Blinking, beeping or any active "identify" command to the Device (the integration is receive-only).
- Inclusion mode filtering of neighbouring Edisio networks.
- Changes to the `edisio_button_event` payload.
- Per-Button names.
- Choosing the Device model (backlog issue).

## Further Notes

- Supersedes the earlier design notes, archived under `docs/specs/archive/`, for the discovery card only.
- Domain terms are defined in `CONTEXT.md`.
- The new options flow reuses the name and area fields defined here; implement this epic first.
