# Beads recipes for the root justfile. Needs scripts/beads.sh, scripts/setup-beads.sh and, for Bitbucket, scripts/git-credential-beads.

# Windows: run just from Git Bash; the recipes call bash scripts.

# Beads task tracking (scripts/beads.sh). init [prefix] prompts for missing setup values; remote operations are bounded.
beads *args:
    scripts/beads.sh {{args}}

# Interactive wizard: pick GitHub or Bitbucket, install tools, set identity, wire the remote, init Beads.
setup-beads:
    scripts/setup-beads.sh
