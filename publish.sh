#!/bin/bash
# Release script — build, check, and upload a package to PyPI.
# Usage: ./publish.sh [version]
#   Without arguments: use current version from the package's __init__.py
#   With argument:     update version in __init__.py and README*.md before release
#
# CHANGELOG.md is never auto-edited. If it has no entry for the version,
# the script will block the release.

set -euo pipefail
cd "$(dirname "$0")"

INIT_FILE=$(grep -l "^__version__ = " */__init__.py 2>/dev/null | head -1)
[ -z "$INIT_FILE" ] && { echo "[Error] No */__init__.py with __version__ found"; exit 1; }
PKG_NAME=$(dirname "$INIT_FILE")

echo "Checking dependencies..."
python3 -c "import build, twine" 2>/dev/null || pip install build twine

if [ -n "${1:-}" ]; then
    VERSION="$1"
    QUOTE=$(sed -n "s/^__version__ = \(.\).*/\1/p" "$INIT_FILE")
    sed -i.bak "s/^__version__ = .*/__version__ = ${QUOTE}${VERSION}${QUOTE}/" "$INIT_FILE"
    rm -f "$INIT_FILE.bak"
    echo "Version updated to $VERSION"
else
    VERSION=$(sed -n "s/^__version__ = [\"']\([^\"']*\)[\"'].*/\1/p" "$INIT_FILE")
fi

# Stamp the version into any README's "**版本**/**Version**: vX.Y.Z" marker line.
# Restricted to that line so other "v5"-style strings (CLI flags, spec URLs) are untouched.
for doc in README*.md; do
    [ -f "$doc" ] && sed -i.bak -E "/\*\*(版本|Version)\*\*/ s/v[0-9]+\.[0-9]+\.[0-9]+/v$VERSION/" "$doc" && rm -f "$doc.bak"
done

echo "Package: $PKG_NAME"
echo "Version: $VERSION"

if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    echo "[Warning] Uncommitted changes in working tree"
    git status --short
    read -p "Continue? (y/N) " confirm
    [ "$confirm" = "y" ] || exit 1
fi

echo "Checking CHANGELOG mentions v$VERSION..."
if [ -f CHANGELOG.md ] && ! grep -q "$VERSION" CHANGELOG.md; then
    echo "[Error] CHANGELOG.md has no entry for $VERSION — add release notes before publishing."
    exit 1
fi

echo "Cleaning old build artifacts..."
rm -rf dist build ./*.egg-info

echo "Building..."
python3 -m build

echo "Checking..."
twine check dist/*

echo "Ready to upload:"
ls -lh dist/
read -p "Upload $PKG_NAME $VERSION to PyPI? (y/N) " confirm
[ "$confirm" = "y" ] || { echo "Cancelled"; exit 1; }

echo "Uploading..."
twine upload dist/*

git tag -a "v$VERSION" -m "Release $VERSION" 2>/dev/null || echo "[Warning] tag v$VERSION already exists"
rm -rf dist build ./*.egg-info

echo ""
echo "Release complete: $PKG_NAME $VERSION"
echo "https://pypi.org/project/$PKG_NAME/"
echo "Push the tag when ready: git push origin v$VERSION"
