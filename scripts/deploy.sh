#!/usr/bin/env bash
# Deploy the integration from this checkout to the HA config share.
# Only runs when invoked. Usage: scripts/deploy.sh [CONFIG_DIR]   (default: /Volumes/config)
set -euo pipefail

CONFIG_DIR="${1:-/Volumes/config}"
SRC="$(cd "$(dirname "$0")/.." && pwd)/custom_components/edisio"
DEST="$CONFIG_DIR/custom_components/edisio"

if [ -d "$DEST" ]; then
  # Outside custom_components/: HA scans every folder in there.
  BACKUP_DIR="$CONFIG_DIR/custom_components_backups"
  mkdir -p "$BACKUP_DIR"
  BACKUP="$BACKUP_DIR/edisio.bak-$(date +%Y%m%d-%H%M%S)"
  cp -R "$DEST" "$BACKUP"
  echo "Backed up $DEST to $BACKUP"
  # Empty it so modules removed from the source don't linger and still get loaded.
  rm -rf "$DEST"
fi

mkdir -p "$DEST"
# cp -f per file: rsync fails on the Samba share. Skip bytecode and dot-files/folders (tool state).
(cd "$SRC" && find . -type f ! -name '*.pyc' ! -path '*/__pycache__/*' ! -path '*/.*' | while read -r f; do
  mkdir -p "$DEST/$(dirname "$f")"
  cp -f "$SRC/$f" "$DEST/$f"
done)

VERSION="$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$SRC/manifest.json")"
REF="$(git -C "$SRC" describe --tags --always --dirty 2>/dev/null || echo unknown)"
echo "Deployed edisio $VERSION from $REF."
echo "Note: Edisio is installed through the Marketplace, which still shows its own installed"
echo "version. Redownload a release from the Marketplace to go back to a clean release."
echo "Fully RESTART Home Assistant (a reload keeps old Python modules), then refresh the browser."
