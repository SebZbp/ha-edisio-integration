# Issue tracker: Beads (`bd`)

Issues for this repo live in the **Beads** database (`.beads/`), managed with the `bd` CLI.

Session rules (pull before, push after, identity, one worker per ticket) live in the `using-beads` skill. This file only records what is specific to this repo.

## Repo facts

- Issue prefix: `edisio`
- Remote: GitHub `origin` (HTTPS); the database lives at `refs/dolt/ha-edisio-integration`; git authenticates through `gh`
- PRs are not tickets: cite the bead id in the PR description
- First-time setup: `just setup-beads` (wizard: host, tools, identity, remote, `just beads init`). Every other workspace: `just beads join`. Git worktrees of this repo share the main checkout's database
- Sync in shared mode: `just beads pull` / `just beads push` (bounded); diagnose with `just beads doctor`

## Conventions

- **Epic**: the named, scoped global objective; top-level, created with `bd create <title> --type epic`.
- **Feature**: a scoped deliverable or development phase, created with `bd create <title> --type feature --parent <epic-id>`. An epic spanning phases has one feature per phase. Each feature has a spec in `docs/specs/` that states the phase objective, scope, and acceptance criteria.
- **Task**: a unit of implementation or decision work, created with `bd create <title> --type task --parent <feature-id>`. Every task must have a feature parent, and every feature must have an epic parent. Never create an orphan task or feature.
- **Bug**: use Beads issue type `bug`. Parent it directly to the feature when clearly related; otherwise parent it to the clearly scoped epic. If the right parent or scope is unclear, ask the user before creating the ticket.
- Before creating tickets, verify or ask the user to name and scope the epic and feature. Do not invent a global objective or feature scope on the user's behalf.
- Structural hierarchy is expressed by Beads issue types and `--parent`; labels identify triage roles or work modes. Use the exact mappings in `triage-labels.md`.
- Dependencies use the native graph: `bd dep add <blocked-id> <blocker-id>`. The issue that depends on another is blocked by it
- `bd ready` is the frontier: open, unblocked work
- `bd close <id> --reason "..."` records completion; the reason is the durable completion record
- Beads status carries lifecycle (`open`, `in_progress`, `blocked`, `closed`); labels carry triage or work-mode tags (see `triage-labels.md`)

## When a skill says "publish to the issue tracker"

- `/to-spec`: create a **feature** under its scoped epic and put its spec in `docs/specs/`; the feature and spec link to each other.
- `/to-tickets`: create each implementation ticket as a **task** under the selected feature. Preserve blocking edges with Beads dependencies.
- `/wayfinder`: create the map as a **feature** under the epic with the `wayfinder:map` label; create each decision ticket as a **task** under the map feature. Map Wayfinder types to `type:research`, `type:prototype`, `type:grilling`, or `type:task` labels.
- For all other proposals, use a feature under the named epic, then tasks under that feature. Ask the user to name and scope missing parents before publishing.
- After creation or any other mutation, run `just beads push`.

## When a skill says "fetch the relevant ticket"

`bd show <id>`. Given only a description, find it with `bd list --title-contains <text>`.

## Specs and durable docs

- Specs live in `docs/specs/`; each spec names its Beads feature and the feature links back to the spec.
- Durable research and project memory live under `docs/memory/`; domain terms live in `CONTEXT.md`; decisions live in `docs/adr/`.
- Any durable document a ticket produces gets a backlink in its Beads issue, so the ticket stays the hub for the work.

## Wayfinding operations

Used by `/wayfinder`:

- **Map**: a feature under its scoped epic. Running "Decisions-so-far" are appended with `bd update <feature-id> --append-notes "<gist + link>"`
- **Child ticket**: a task under the map feature. The wayfinder `Type:` line becomes a label: `type:research`, `type:prototype`, `type:grilling`, or `type:task`
- **Blocking**: native dependency graph
- **Frontier**: `bd ready --unassigned --parent <feature-id>`
- **Claim**: `bd update <id> --claim`, then `just beads push` (the claim only counts once pushed)
- **Resolve**: `bd close <id> --reason "<answer gist>"`, then `bd update <feature-id> --append-notes "<gist + link to the closed child>"`, then `just beads push`
