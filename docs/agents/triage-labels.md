# Triage and Work-Type Tags

Use the five canonical triage labels as Beads labels. Ticket status remains the lifecycle (`open`, `in_progress`, `blocked`, `closed`); labels are tags for triage and work mode.

| Canonical triage role | Beads label | Meaning |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | A maintainer needs to evaluate this issue |
| `needs-info` | `needs-info` | Waiting on the user or another person for specific information; use a Beads human gate as well when available |
| `ready-for-agent` | `ready-for-agent` | Fully specified and available for agent work |
| `ready-for-human` | `ready-for-human` | Needs human implementation; agents filter it out with `bd ready --exclude-label ready-for-human` |
| `wontfix` | `wontfix` | Will not be actioned; close with a reason and keep the label for filtering |

## Triage category

The triage skill also asks for a `bug` or `enhancement` category. Represent bugs with Beads issue type `bug` (not a duplicate `bug` label). Represent enhancement category with the `enhancement` label when needed; structural types remain `epic`, `feature`, `task`, and `bug`.

## Work-type tags

Apply the appropriate `type:` label to Wayfinder decision tasks so the work mode is queryable in Beads:

| Work type | Beads label |
| --- | --- |
| Research | `type:research` |
| Prototype | `type:prototype` |
| Grilling | `type:grilling` |
| Implementation or other task | `type:task` |

Use structural issue types and parent links for the Epic → Feature → Task hierarchy; these tags never replace the parent relationship. A feature uses Beads type `feature`, and a bug uses type `bug`.

When a skill names a triage role or work type, apply its exact label from this table. Starting work is separate from triage: claim with `bd update <id> --claim`, then `just beads push`.
