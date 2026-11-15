#!/usr/bin/env bash
# Beads remote lifecycle for one repo. Copy verbatim from the using-beads skill to scripts/beads.sh.
# The Dolt database lives at refs/dolt/<factory> on origin, which is GitHub or Bitbucket (HTTPS):
#   GitHub     git authenticates through the GitHub CLI (gh auth setup-git)
#   Bitbucket  git authenticates as x-token-auth with a repository access token kept in
#              AWS Secrets Manager, served by scripts/git-credential-beads
# Commands:
#   install        install the Beads CLI from its checksum-verifying upstream installer
#   init [prefix]  first user: prompts for missing setup values when run interactively
#   join           every other workspace: register auth, bootstrap from refs/dolt/<factory>
#   pull | push    bounded sync; a no-op in local-only mode (no sync.remote)
#   doctor         read-only diagnosis: identity, mode, auth, processes, locks
#   secret-path    Bitbucket only: print the AWS secret path the credential helper reads
# Remote steps never prompt and stop after BEADS_TIMEOUT seconds (default 120).
# Needs GNU timeout (or gtimeout) and jq; flock when present. macOS: brew install coreutils flock jq.
# Windows: run from Git Bash (it ships GNU timeout); without flock, a lock directory serializes remote steps.
set -euo pipefail
cd "$(dirname "$0")/.."
export BEADS_ACTOR="${BEADS_ACTOR:-$(git config --local beads.actor || true)}"

die() { echo "beads: $*" >&2; exit 1; }
T="${BEADS_TIMEOUT:-120}"
export GIT_TERMINAL_PROMPT=0 BD_NO_REMOTE_ADOPT=1
# VS Code's askpass opens a username/password dialog that GIT_TERMINAL_PROMPT=0 does not suppress.
unset GIT_ASKPASS SSH_ASKPASS

case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) WINDOWS=true ;; *) WINDOWS=false ;; esac

# EXIT handlers run last-registered first: on_exit "command".
CLEANUP=":"
trap 'eval "$CLEANUP"' EXIT
on_exit() { CLEANUP="$1; $CLEANUP"; }

# Paths handed to native Windows programs (git URLs, bd) need C:/... form; a no-op elsewhere.
native_path() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s\n' "$1"; fi; }
file_url() { local p; p="$(native_path "$1")"; case "$p" in /*) echo "file://$p" ;; *) echo "file:///$p" ;; esac; }

# GNU timeout only: Windows ships an unrelated timeout.exe that may come first on PATH.
TIMEOUT=""
for t in timeout gtimeout; do
  if command -v "$t" >/dev/null 2>&1 && "$t" --version 2>/dev/null | grep -q GNU; then TIMEOUT="$t"; break; fi
done
# stdin from /dev/null: under timeout the child is not in the terminal's foreground group, so any tty read stops it.
bounded() {
  [ -n "$TIMEOUT" ] || die "GNU timeout missing (macOS: brew install coreutils; Windows: run from Git Bash)"
  "$TIMEOUT" --kill-after=10 "$T" "$@" </dev/null
}
# One remote operation at a time per workspace; a second caller fails instead of queueing on Beads locks.
LOCK=.beads/remote-op.lock          # flock file
LOCK_DIR=.beads/remote-op.dir.lock  # fallback without flock (Git Bash): a directory holding the owner's PID
serialize() {
  local waited=0 pid
  mkdir -p .beads
  if command -v flock >/dev/null 2>&1; then
    exec 9>"$LOCK"
    flock -w "$T" 9 || die "another beads remote operation holds $LOCK; run 'just beads doctor'"
    return
  fi
  until mkdir "$LOCK_DIR" 2>/dev/null; do
    pid="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then rm -rf "$LOCK_DIR"; continue; fi   # owner died
    [ "$waited" -lt "$T" ] || die "another beads remote operation holds $LOCK_DIR; run 'just beads doctor'"
    sleep 1; waited=$((waited + 1))
  done
  echo $$ > "$LOCK_DIR/pid"
  on_exit "rm -rf '$LOCK_DIR'"
}

ask_required() {
  local label="$1" default="${2:-}" remediation="${3:-set the missing value}" value
  if [[ ! -r /dev/tty || ! -w /dev/tty ]]; then
    die "missing $label; $remediation, or rerun init from an interactive terminal"
  fi
  while :; do
    if [ -n "$default" ]; then
      printf '%s [%s]: ' "$label" "$default" >/dev/tty
    else
      printf '%s: ' "$label" >/dev/tty
    fi
    IFS= read -r value </dev/tty || die "could not read $label from the terminal"
    value="${value:-$default}"
    [ -n "$value" ] && { printf '%s\n' "$value"; return; }
    echo "$label is required (Ctrl-C to cancel)." >/dev/tty
  done
}

factory_name() { echo "${BEADS_FACTORY:-${CONVEYOR_PROJECT_NAME:-$(git config --local beads.factory || true)}}"; }

# remote_for_origin URL: the sync.remote for an HTTPS GitHub or Bitbucket origin; fails otherwise.
remote_for_origin() {
  local url="${1%.git}" rest
  case "$url" in
    https://github.com/*/*) echo "git+$url" ;;
    https://*bitbucket*/*/*)
      rest="${url#https://}"; rest="${rest#*@}"
      echo "git+https://x-token-auth@$rest" ;;
    *) return 1 ;;
  esac
}

prepare_init_inputs() {
  local prefix="${1:-}" actor git_name git_email origin factory

  [ -n "$prefix" ] || prefix="$(ask_required 'Beads issue prefix' '' 'pass it as just beads init <prefix>')"

  factory="$(factory_name)"
  if [ -z "$factory" ]; then
    factory="$(ask_required 'Beads factory name (names refs/dolt/<factory>)' "$(basename "$PWD")" 'set BEADS_FACTORY')"
  fi
  git config --local beads.factory "$factory"

  actor="${BEADS_ACTOR:-$(git config user.name || true)}"
  if [ -z "$actor" ] || [ "$actor" = conveyor ]; then
    actor="$(ask_required 'Beads actor handle (BEADS_ACTOR)' '' 'set BEADS_ACTOR')"
    INIT_ACTOR_PROMPTED=true
  fi
  export BEADS_ACTOR="$actor"
  git config --local beads.actor "$actor"

  git_name="$(git config user.name || true)"
  if [ -z "$git_name" ] || [ "$git_name" = conveyor ]; then
    git_name="$(ask_required 'Git author name' '' 'set git config user.name')"
    git config --local user.name "$git_name"
  fi
  git_email="$(git config user.email || true)"
  if [ -z "$git_email" ]; then
    git_email="$(ask_required 'Git author email' '' 'set git config user.email')"
    git config --local user.email "$git_email"
  fi

  origin="$(git remote get-url origin 2>/dev/null || true)"
  if [ -z "$origin" ]; then
    origin="$(ask_required 'HTTPS GitHub or Bitbucket origin URL (added as remote origin)' '' 'configure git remote origin')"
    remote_for_origin "$origin" >/dev/null || die "origin must be an HTTPS GitHub or Bitbucket URL"
    git remote add origin "$origin" || die "could not add the origin remote"
  elif ! remote_for_origin "$origin" >/dev/null; then
    die "origin must be an HTTPS GitHub or Bitbucket URL for Beads init (found '$origin'); update the origin remote and retry"
  fi

  INIT_PREFIX="$prefix"
}

check_actor() {
  local actor="${BEADS_ACTOR:-$(git config user.name || true)}"
  [ -n "$actor" ] && [ "$actor" != conveyor ] && return
  echo "Set your identity first (shared containers often give every user the same \$USER):" >&2
  echo '  git config --global user.name "<name>"; git config --global user.email "<email>"' >&2
  echo "  echo 'export BEADS_ACTOR=\"<handle>\"' >> ~/.zshrc   # or ~/.bashrc" >&2
  exit 1
}

configured_remote() {   # prints sync.remote, fails in local-only mode
  local r; r="$(bd config get sync.remote 2>/dev/null || true)"
  case "$r" in
    git+https://github.com/*/*|git+https://x-token-auth@*/*/*) echo "$r" ;;
    *) return 1 ;;
  esac
}

derive() {   # $1 = sync.remote (git+https://github.com/<owner>/<repo> or git+https://x-token-auth@<host>/<workspace>/<repo>)
  local host repo env
  REMOTE="$1"; GIT_URL="${REMOTE#git+}"
  FACTORY="$(factory_name)"
  [ -n "$FACTORY" ] || die "factory name missing; set BEADS_FACTORY or run 'just beads init' interactively"
  REF="${BEADS_REF:-refs/dolt/$FACTORY}"
  case "$GIT_URL" in
    https://github.com/*)
      KIND=github
      SECTION="credential.https://github.com.helper"
      AUTH_HINT="check the repo exists and 'gh auth status'" ;;
    *)
      KIND=bitbucket
      host="${GIT_URL#https://x-token-auth@}"; host="${host%%/*}"
      repo="${GIT_URL##*/}"; repo="${repo%.git}"
      env="${CONVEYOR_ENVIRONMENT_NAME:-dev}"
      SECRET="${BEADS_SECRET_PATH:-/data_product/prm/${env:0:3}/$FACTORY/git/bitbucket/$repo}"
      SECTION="credential.https://x-token-auth@$host.helper"
      HELPER="$HOME/.local/bin/git-credential-beads"
      AUTH_HINT="provision the token at $SECRET and refresh your AWS session" ;;
  esac
}

install_helper() {
  # Global, not repo-local: Dolt runs git from its own cache dir, outside this repo's config.
  local want have
  if [ "$KIND" = github ]; then
    command -v gh >/dev/null 2>&1 || die "GitHub CLI missing (macOS: brew install gh; Windows: winget install --id GitHub.cli)"
    bounded gh auth status --hostname github.com >/dev/null 2>&1 \
      || die "gh is not signed in to github.com; run 'gh auth login'"
    gh auth setup-git --hostname github.com >/dev/null
  else
    want="$HELPER $SECRET"
    have="$(git config --global --get-all "$SECTION" | grep -v '^$' || true)"
    if [ -n "$have" ] && [ "$have" != "$want" ] && [ -z "${BEADS_FORCE_HELPER:-}" ]; then
      die "$SECTION already serves '$have'. Set BEADS_FORCE_HELPER=1 to replace it with '$want'"
    fi
    mkdir -p "$(dirname "$HELPER")"
    install -m 0755 scripts/git-credential-beads "$HELPER"
    git config --global --unset-all "$SECTION" || true
    git config --global --add "$SECTION" ""   # reset inherited keychain/libsecret/oauth helpers
    git config --global --add "$SECTION" "$want"
  fi
  git config beads.role maintainer          # silences "beads.role not configured"
}

probe() {   # 0 = ref exists, 2 = ref missing, other = auth/network failure. Runs outside the repo to test global config.
  (cd "$(mktemp -d)" && bounded git ls-remote --exit-code "$GIT_URL" "$REF" >/dev/null)
}

state_file() { echo ".beads/embeddeddolt/$(jq -r .dolt_database .beads/metadata.json)/.dolt/repo_state.json"; }

set_ref() {   # name must be set: an empty one makes 'bd dolt pull' fail with "invalid fetch spec: 'main'"
  local state; state="$(state_file)"
  jq --arg url "$REMOTE" --arg ref "$REF" '.remotes.origin.name = "origin" | .remotes.origin.url = $url
    | .remotes.origin.fetch_specs //= ["refs/heads/*:refs/remotes/origin/*"] | .remotes.origin.params.git_ref = $ref' \
    "$state" > "$state.new"
  mv "$state.new" "$state"
}

cmd_init() {
  local prefix origin_url head empty rc=0
  prepare_init_inputs "${1:-}"
  prefix="$INIT_PREFIX"
  check_actor
  origin_url="$(git config --get remote.origin.url)"
  derive "${BEADS_REMOTE:-$(remote_for_origin "$origin_url")}"
  install_helper
  probe || rc=$?
  case $rc in
    2) ;;
    0) die "$REF already exists on $GIT_URL: run 'just beads join'" ;;
    *) die "cannot read $GIT_URL (rc=$rc): $AUTH_HINT" ;;
  esac
  # Dolt cannot push to a git remote that has no branch yet.
  [ -n "$(bounded git ls-remote --heads "$GIT_URL" 2>/dev/null || true)" ] \
    || die "$GIT_URL has no branches yet. Push one first ('git push -u origin $(git branch --show-current)'), then rerun init"
  serialize
  if [ ! -e .beads/metadata.json ]; then
    head="$(git rev-parse HEAD)"
    # bd init probes origin for refs/dolt/data without credentials; our data lives at $REF, so answer it from an empty repo.
    empty="$(mktemp -d)"; git init -q --bare "$empty"
    GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=credential.helper GIT_CONFIG_VALUE_0='' \
      GIT_CONFIG_KEY_1="url.$(file_url "$empty").insteadOf" GIT_CONFIG_VALUE_1="$origin_url" \
      bounded bd init --prefix "$prefix" --non-interactive --role maintainer --skip-agents --skip-hooks \
      || { rm -rf "$empty"; die "bd init failed; run 'just beads doctor'"; }
    rm -rf "$empty"
    [ "$(git rev-parse HEAD)" = "$head" ] || echo "beads: bd init made a git commit; review it with 'git show --stat HEAD'"
  fi
  bd config set sync.remote "$REMOTE" >/dev/null
  bd config set dolt.auto-push false >/dev/null   # background pushes cannot be bounded; push explicitly
  set_ref
  bounded bd dolt push || die "first push failed (rc=$?); run 'just beads doctor'"
  probe || die "push finished but $REF is not visible on $GIT_URL"
  echo "Shared mode: $REF on $GIT_URL. Commit .beads/config.yaml so others can 'just beads join'."
  if [ "${INIT_ACTOR_PROMPTED:-false}" = true ]; then
    printf 'Persist your Beads identity in your shell profile: export BEADS_ACTOR=%q\n' "$BEADS_ACTOR"
  fi
}

cmd_join() {
  local r rc=0 state fresh=false mirror mgit empty
  check_actor
  r="$(configured_remote)" || die "no sync.remote in .beads/config.yaml (local-only). First user: 'just beads init <prefix>'"
  derive "$r"
  install_helper
  probe || rc=$?
  case $rc in
    0) ;;
    2) die "$REF not found on $GIT_URL. First user: 'just beads init <prefix>'" ;;
    *) die "cannot read $GIT_URL (rc=$rc): $AUTH_HINT" ;;
  esac
  serialize
  state="$(state_file)"
  if [ ! -e "$state" ]; then
    mirror="$(mktemp -d)"; mgit="$(native_path "$mirror/repo.git")"
    cp .beads/config.yaml "$mirror/config.yaml"
    # bd bootstrap persists the mirror URL into config.yaml; put the committed file back whatever happens.
    on_exit "cp '$mirror/config.yaml' .beads/config.yaml; rm -rf '$mirror'"
    # bd bootstrap only reads refs/dolt/data, so mirror our ref there first (clone needs a branch too).
    git init -q --bare "$mgit"
    bounded git --git-dir="$mgit" fetch -q "$GIT_URL" "$REF:refs/dolt/data"
    empty="$(git --git-dir="$mgit" hash-object -t tree -w /dev/null)"
    export GIT_AUTHOR_NAME=beads GIT_AUTHOR_EMAIL=beads@localhost GIT_COMMITTER_NAME=beads GIT_COMMITTER_EMAIL=beads@localhost
    git --git-dir="$mgit" update-ref refs/heads/main \
      "$(git --git-dir="$mgit" commit-tree "$empty" -m init)"
    BD_SYNC_REMOTE="git+$(file_url "$mirror/repo.git")" bounded bd bootstrap --yes
    cp "$mirror/config.yaml" .beads/config.yaml
    fresh=true
  fi
  set_ref
  # Only pull right after a bootstrap: nothing local can be lost yet.
  if $fresh; then bounded bd dolt pull; fi
  echo "Shared mode: $REF on $GIT_URL. Sync with 'just beads pull' / 'just beads push'."
}

cmd_sync() {
  local rc=0
  configured_remote >/dev/null || { echo "beads: local-only mode, $1 skipped"; return 0; }
  serialize
  bounded bd dolt "$1" || rc=$?
  [ $rc -eq 0 ] || die "bd dolt $1 failed (rc=$rc$([ $rc -ge 124 ] && echo ', timed out')). Run 'just beads doctor' before retrying"
}

cmd_install() {
  if command -v bd >/dev/null 2>&1; then
    echo "Beads is already installed: $(command -v bd)"
    bd version
    return
  fi
  command -v curl >/dev/null 2>&1 || die "curl is required to install Beads"

  local installer bd_path win_dir
  if $WINDOWS; then
    # The bash installer refuses Windows; the official PowerShell one verifies checksums too.
    bounded powershell.exe -NoProfile -Command \
      "irm https://raw.githubusercontent.com/gastownhall/beads/main/install.ps1 | iex" \
      || die "Beads installation failed"
    win_dir="$(cygpath -u "$LOCALAPPDATA")/Programs/bd"
    command -v bd >/dev/null 2>&1 || [ ! -x "$win_dir/bd.exe" ] \
      || echo "Add bd to PATH: echo 'export PATH=\"\$PATH:$win_dir\"' >> ~/.bashrc, then open a new Git Bash"
    PATH="$PATH:$win_dir" bd version || die "installer finished, but bd is not available; check your PATH"
    return
  fi
  installer="$(mktemp)"
  bounded curl -fsSL https://raw.githubusercontent.com/gastownhall/beads/main/scripts/install.sh -o "$installer" \
    || { rm -f "$installer"; die "could not download the official Beads installer"; }
  PATH="$PATH:$HOME/.local/bin" bounded bash "$installer" \
    || { rm -f "$installer"; die "Beads installation failed"; }
  rm -f "$installer"

  bd_path="$(command -v bd || true)"
  [ -n "$bd_path" ] || { [ -x "$HOME/.local/bin/bd" ] && bd_path="$HOME/.local/bin/bd"; }
  [ -n "$bd_path" ] || die "installer finished, but bd is not available; check your PATH"
  "$bd_path" version
}

cmd_secret_path() {
  local origin r
  origin="$(git remote get-url origin 2>/dev/null)" || die "no origin remote"
  r="$(remote_for_origin "$origin")" || die "origin is not an HTTPS GitHub or Bitbucket URL"
  derive "$r"
  [ "$KIND" = bitbucket ] || die "secret-path applies to Bitbucket only; GitHub uses gh auth"
  echo "$SECRET"
}

cmd_doctor() {
  local r rc=0
  echo "actor:    ${BEADS_ACTOR:-<unset>} (git user.name: $(git config user.name || echo '<unset>'))"
  if r="$(configured_remote)"; then
    derive "$r"
    echo "mode:     shared, $KIND ($REMOTE)"
    echo "ref:      $(jq -r '.remotes.origin.params.git_ref // "<unset>"' "$(state_file)" 2>/dev/null || echo '<no db>') (expected $REF)"
    echo "helper:   $(git config --global --get-all "$SECTION" | grep -v '^$' || echo '<not registered globally>')"
    T="${BEADS_TIMEOUT:-30}"; probe || rc=$?
    case $rc in
      0) echo "probe:    ok" ;;
      2) echo "probe:    auth ok, $REF missing" ;;
      *) echo "probe:    FAILED rc=$rc ($AUTH_HINT)" ;;
    esac
  else
    echo "mode:     local-only (no sync.remote)"
  fi
  if command -v flock >/dev/null 2>&1; then
    echo "remote op lock: $(flock -n "$LOCK" true 2>/dev/null && echo free || echo HELD)"
  elif [ -d "$LOCK_DIR" ]; then
    echo "remote op lock: HELD by pid $(cat "$LOCK_DIR/pid" 2>/dev/null || echo '?') ($LOCK_DIR; remove it if that process is gone)"
  else
    echo "remote op lock: free"
  fi
  echo "processes (bd, dolt, credential helpers):"
  # Git Bash's ps has no -o; -efW also lists native Windows processes such as bd.exe.
  { ps -eo pid,etime,args 2>/dev/null || ps -efW 2>/dev/null; } \
    | grep -iE '(^|[ /\\])(bd|dolt|git-credential-[a-z]+)(\.exe)?( |$)' | grep -v grep || echo "  none"
  echo "lock files: $(ls .beads/*.lock* 2>/dev/null | tr '\n' ' ')"
}

case "${1:-}" in
  install) cmd_install ;;
  init) shift; cmd_init "$@" ;;
  join) cmd_join ;;
  pull|push) cmd_sync "$1" ;;
  doctor) cmd_doctor ;;
  secret-path) cmd_secret_path ;;
  *) die "usage: beads.sh install | init [prefix] | join | pull | push | doctor | secret-path" ;;
esac
