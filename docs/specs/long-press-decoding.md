# Long-press decoding: one hold = one long_press

Tracker: beads epic `edisio-s4h` (label `needs-info`, blocked on the manual capture below)

## Problem Statement

The packet decoder maps command `07` to `up`, which the integration reports as a long press, and command `08` (DIM-STOP) to `toggle`, which it reports as a short press. If holding a Button sends `07` and then `08` on release, one physical long press fires a `long_press` event followed by a `short_press` event, and automations bound to the short press run by mistake. A long press has never been observed with this plugin, so the actual packet sequence of a hold is unknown.

## Solution

First capture what a hold really sends. Then decode it so that one physical hold fires exactly one `edisio_button_event` with `type: long_press`: no `short_press` on release, no repeats while holding. A short press keeps firing exactly one `short_press`. The event payload is unchanged.

## Manual test (blocking)

Run by the home owner on the live installation; record the result as a comment on the capture issue.

1. Enable debug logging for the integration (`logger: logs: custom_components.edisio: debug`) and reload.
2. On Device `06709603` (BP Bas escalier), short-press Button `05` once; note the log lines "Raw data received" / "Edisio Packet Extracted" and the `edisio_button_event` events (Developer tools → Events → listen to `edisio_button_event`).
3. Hold Button `05` for about 2 seconds, then release; note the same.
4. Hold Button `05` for about 5 seconds, then release; note the same.
5. Repeat steps 2–4 on a second Button (e.g. `07`) to confirm the pattern is not Button-specific.
6. For each packet, record the timestamp, command byte (`cmd`, bytes 24–25 of the packet hex) and Button number.

The questions to answer: what command(s) a hold sends at start, whether they repeat while held and at what interval, whether a `08` (or another command) is sent on release, and how a short press differs.

## User Stories

1. As an automation author, I want a held Button to fire exactly one `long_press` event, so that a long-press automation runs once.
2. As an automation author, I want a held Button not to also fire a `short_press`, so that short-press automations do not run by mistake.
3. As an automation author, I want a short press to keep firing exactly one `short_press`, so that existing automations are unaffected.
4. As an automation author, I want the `edisio_button_event` payload (`device_id`, `button`, `type`) unchanged, so that migrated RFPlayer automations keep working.
5. As a home owner, I want the Button sensor to show "long-press" once per hold, so that its state matches the event.
6. As a maintainer, I want the decoding rules backed by a recorded real packet capture, so that they are not guesswork.

## Implementation Decisions

- Decisions fixed now (independent of the capture):
  - One physical press yields exactly one event, either `short_press` or `long_press` (glossary: Short press / Long press).
  - No repeat events while holding; dimming by hold is out of scope.
  - Payload keys and values are unchanged; only which packets produce an event changes.
  - The Button sensor follows the same rule as the event.
- To be decided from the capture (filled in when `needs-info` is lifted):
  - Which command marks the start of a long press and whether repeats must be suppressed (per Device and Button, within a time window).
  - Whether the release command (`08` or other) must be swallowed when it follows a long-press start for the same Device and Button.
  - The time window values, derived from the measured intervals.
- If the capture shows that a hold sends only a single distinct command and no release, the fix reduces to a mapping correction.
- ADRs: none exist; no contradiction.

## Testing Decisions

- Tests feed recorded packet sequences (from the capture, as hex strings) through the integration's packet-to-event path and assert the `edisio_button_event` events fired, with controlled time. No private helpers.
- Cases: short press → one `short_press`; 2 s hold → one `long_press`, no `short_press`; 5 s hold → one `long_press`; two short presses in quick succession → two `short_press`; holds on two Buttons of the same Device → one `long_press` each.
- Prior art: `tests/test_edisio_api.py`, `tests/test_init.py`.

## Out of Scope

- Repeat-while-held events or dimming.
- New event types (double press, release) or payload changes.
- Other command values beyond those observed in the capture.

## Further Notes

- The capture is the first child task (`ready-for-human`); implementation is blocked on it.
- Domain terms are defined in `CONTEXT.md`.
