#!/usr/bin/env bash
# PreToolUse(Bash): run `bd sync` before any bd command that changes a ticket's state.
# Exit 2 (blocks the command) only on a real sync failure; no remote = skip silently.
cmd=$(jq -r '.tool_input.command // ""')
echo "$cmd" | grep -Eq '(^|[;&|[:space:]])bd[[:space:]]+(create|update|close|reopen|claim|unclaim|set-state|label[[:space:]]+(add|remove)|tag|defer|ready[[:space:]].*--claim)' || exit 0
bd dolt remote list 2>/dev/null | grep -q . || exit 0
out=$(bd sync 2>&1); rc=$?
if [ $rc -ne 0 ]; then
  echo "bd sync failed (exit $rc) before state change — resolve first:" >&2
  echo "$out" >&2
  exit 2
fi
exit 0
