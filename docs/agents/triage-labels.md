# Triage Labels

Triage roles are beads labels, orthogonal to beads' native statuses (`bd statuses`).

| Label in mattpocock/skills | Representation in beads | Meaning |
| --- | --- | --- |
| `needs-triage` | label `needs-triage`, status `open` | Maintainer needs to evaluate this issue |
| `needs-info` | label `needs-info`, status `blocked` (or `deferred`) | Waiting on reporter for more information |
| `ready-for-agent` | label `ready-for-agent`, status `open` (shows in `bd ready`) | Fully specified, ready for an AFK agent |
| `ready-for-human` | label `ready-for-human`, status `open` | Requires human implementation |
| `wontfix` | label `wontfix` + `bd close <id> -r wontfix` | Will not be actioned |

Rules:
- One triage label at a time: `bd label remove` the old one before adding the new one.
- Never mirror a native status as a label (`in_progress`, `closed`, ...).
- Agents only pick up `bd ready -l ready-for-agent`.
- Each change is a state change: the sync hook runs first (see `issue-tracker.md`).
