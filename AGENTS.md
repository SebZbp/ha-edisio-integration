# Agent Instructions

## Task tracking

This repo tracks work in Beads (`bd`). Every ticket you work on, whether the user names its ID or you pick it from `bd ready`, follows this loop:

1. Start: `just beads pull`, `bd update <id> --claim`, `just beads push`. The ticket shows `in_progress` with your assignee before any work begins.
2. Finish: `bd close <id> --reason "..."`, `just beads push`.

On a sync failure or timeout, run `just beads doctor` and report its output.

Before creating, splitting, triaging, or navigating tickets, read `docs/agents/issue-tracker.md` (Epic → Feature → Task hierarchy, parenting rules) and `docs/agents/triage-labels.md`. For identity, blockers, handoff, setup and recovery, use the `using-beads` skill.

## Non-Interactive Shell Commands

**ALWAYS use non-interactive flags** with file operations to avoid hanging on confirmation prompts.

Shell commands like `cp`, `mv`, and `rm` may be aliased to include `-i` (interactive) mode on some systems, causing the agent to hang indefinitely waiting for y/n input.

**Use these forms instead:**
```bash
# Force overwrite without prompting
cp -f source dest           # NOT: cp source dest
mv -f source dest           # NOT: mv source dest
rm -f file                  # NOT: rm file

# For recursive operations
rm -rf directory            # NOT: rm -r directory
cp -rf source dest          # NOT: cp -r source dest
```

**Other commands that may prompt:**
- `scp` - use `-o BatchMode=yes` for non-interactive
- `ssh` - use `-o BatchMode=yes` to fail instead of prompting
- `apt-get` - use `-y` flag
- `brew` - use `HOMEBREW_NO_AUTO_UPDATE=1` env var

## Build & Test

```bash
uv sync        # install dependencies
uv run pytest  # run the test suite
```

## Agent skills

### Issue tracker

Beads (`bd`, prefix `edisio`), shared through `origin` on GitHub; specs in `docs/specs/`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default triage roles as beads labels, plus `type:*` work tags. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context. See `docs/agents/domain.md`.
