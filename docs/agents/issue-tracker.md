# Issue tracker: beads

Issues live in beads (`bd`, Dolt database in `.beads/`, prefix `edisio`). Do not use `gh issue` or `.scratch/`.

## Publish to the issue tracker
- Ticket: `bd create "<title>" -t <task|bug|feature> -p <0-4> -l needs-triage -d "<description>"`
- Spec / large effort: write the spec file (see Specs), then `bd create ... -t epic` with the spec path in the description; child tickets use `--parent <epic-id>`
- Quick capture: `bd q "<title>"` (prints only the ID)

## Specs
Specs are saved in `docs/specs/<feature-slug>.md` (committed to git). The matching epic's description links to that path, and the spec's header records the epic id.

## Fetch a ticket
`bd show <id>` (`--json` for structured output). Search: `bd search <text>`, `bd list`, `bd query`.

## Comments / notes
`bd comment <id> "<text>"` for discussion, `bd note <id> "<text>"` for working notes.

## Dependencies (use systematically)
- Blocking: `bd dep add <child> <blocker>` (or `bd link`). A blocked ticket drops out of `bd ready` automatically.
- Inspect: `bd graph`, `bd dep tree <id>`, `bd children <epic>`.
- Duplicate / replaced: `bd duplicate <id> --of <other>`, `bd supersede`.

## Lifecycle (native statuses, see `bd statuses`)
| Step | Command |
| --- | --- |
| Find available work | `bd ready` |
| Claim (atomic) | `bd update <id> --claim` or `bd ready --claim` |
| Long task | `bd heartbeat <id>` to keep the lease |
| Give up | `bd unclaim <id>` |
| Done | `bd close <id> -r "<reason>"` |
| Reopen | `bd reopen <id>` |

## Sync before every state change
Before any command that changes a ticket's state (`update`, `close`, `reopen`, `unclaim`, `set-state`, `label add|remove`, `ready --claim`), run `bd sync` (pull, conflict check, recompute blocked flags, push).
This is enforced by the PreToolUse hook `.claude/hooks/bd-sync-before-change.sh`, which blocks the command if the sync fails (exit 2 = merge conflict, resolve by hand with `bd conflicts`). If no Dolt remote is configured (`bd dolt remote list` empty) the sync is skipped.

## Wayfinding (/wayfinder)
- **Map**: a beads epic (`-t epic`) whose description holds the Notes / Decisions-so-far / Fog body.
- **Child ticket**: child of the epic (`--parent`), label `type:research|prototype|grilling|task`.
- **Blocking**: `bd dep add`.
- **Frontier**: `bd ready` restricted to `bd children <epic>`.
- **Claim**: `bd update <id> --claim`.
- **Resolve**: answer as `bd comment`, `bd close`, then append a pointer (gist + id) to the epic's Decisions-so-far.

## PRs
GitHub PRs are not tickets; cite the beads id in the PR description.
