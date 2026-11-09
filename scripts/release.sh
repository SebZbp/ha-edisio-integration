#!/usr/bin/env bash
# Cut a release. Usage: scripts/release.sh X.Y.Z
#
# main only accepts changes through pull requests, so a release takes two runs:
#   1. origin/main's manifest is not X.Y.Z yet: bump it on branch release/vX.Y.Z,
#      push that branch and open a PR. Merge it once CI is green.
#   2. origin/main's manifest is X.Y.Z: tag that commit vX.Y.Z and push the tag
#      (asks first). .github/workflows/release.yml then validates and publishes
#      the GitHub Release that the Marketplace installs from.
set -euo pipefail

VERSION="${1:-}"
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Usage: $0 X.Y.Z" >&2
  exit 2
fi
TAG="v$VERSION"
MANIFEST="custom_components/edisio/manifest.json"

cd "$(dirname "$0")/.."

if [ -n "$(git status --porcelain)" ]; then
  echo "Working tree is not clean; commit or stash first." >&2
  exit 1
fi

git fetch --quiet --tags origin main
if git rev-parse --quiet --verify "refs/tags/$TAG" >/dev/null; then
  echo "Tag $TAG already exists." >&2
  exit 1
fi

manifest_version() {
  sed -n 's/.*"version": *"\([^"]*\)".*/\1/p'
}
MAIN_VERSION="$(git show "origin/main:$MANIFEST" | manifest_version)"

if [ "$MAIN_VERSION" = "$VERSION" ]; then
  # Phase 2: the bump is on main, tag it.
  COMMIT="$(git rev-parse origin/main)"
  echo "origin/main ($(git log -1 --format='%h %s' "$COMMIT")) has version $VERSION."
  read -r -p "Tag it $TAG and push the tag (publishes the release)? [y/N] " answer
  [ "$answer" = "y" ] || [ "$answer" = "Y" ] || { echo "Aborted."; exit 1; }
  git tag -a "$TAG" -m "$TAG" "$COMMIT"
  git push origin "refs/tags/$TAG"
  echo "Pushed $TAG. Follow the release workflow with: gh run watch"
  exit 0
fi

# Phase 1: open a version-bump PR from origin/main.
BRANCH="release/$TAG"
echo "origin/main is at version $MAIN_VERSION; preparing $VERSION on $BRANCH."
git switch --quiet -c "$BRANCH" origin/main
sed -i.bak "s/\"version\": *\"$MAIN_VERSION\"/\"version\": \"$VERSION\"/" "$MANIFEST"
rm -f "$MANIFEST.bak"
if [ "$(manifest_version <"$MANIFEST")" != "$VERSION" ]; then
  echo "Failed to set version in $MANIFEST." >&2
  exit 1
fi
uv run pytest -q
git commit --quiet -m "chore: release $TAG" -- "$MANIFEST"
git push --quiet -u origin "$BRANCH"
gh pr create --base main --head "$BRANCH" --title "chore: release $TAG" \
  --body "Bump manifest version to $VERSION. After merging, run \`scripts/release.sh $VERSION\` again to tag and publish."
echo "Merge the PR once CI is green, then run: $0 $VERSION"
