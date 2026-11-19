#!/usr/bin/env bash
# Build and validate the release before creating/pushing a tag.
set -Eeuo pipefail

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
    echo "Usage: ./publish.sh 0.4.1" >&2
    exit 2
fi

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([a-zA-Z0-9.+-]*)?$ ]]; then
    echo "Invalid version: $VERSION" >&2
    exit 2
fi

if [[ "$(git branch --show-current)" != "main" ]]; then
    echo "Release must be prepared from the main branch." >&2
    exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
    echo "Working tree must be clean before preparing a release." >&2
    exit 1
fi
if git rev-parse -q --verify "refs/tags/v$VERSION" >/dev/null; then
    echo "Tag v$VERSION already exists." >&2
    exit 1
fi

echo "Preparing fsresource-tree $VERSION"

# The version is dynamic in pyproject.toml and comes from this source file.
python3 - "$VERSION" <<'PY'
from pathlib import Path
import re
import sys

path = Path("fsresourcetree/__init__.py")
source = path.read_text(encoding="utf-8")
updated, count = re.subn(
    r'^__version__ = "[^"]+"$',
    f'__version__ = "{sys.argv[1]}"',
    source,
    count=1,
    flags=re.MULTILINE,
)
if count != 1:
    raise SystemExit("Could not locate exactly one __version__ declaration.")
path.write_text(updated, encoding="utf-8")
PY

cleanup() {
    if [[ -z "$(git rev-parse -q --verify HEAD 2>/dev/null || true)" ]]; then
        return
    fi
    if ! git rev-parse -q --verify "refs/tags/v$VERSION" >/dev/null; then
        git checkout -- fsresourcetree/__init__.py >/dev/null 2>&1 || true
    fi
}
trap cleanup ERR

echo "[1/5] Run tests"
python3 -m pytest -q

echo "[2/5] Check diff and build distributions"
git diff --check
rm -rf dist build
python3 -m build --sdist --wheel
python3 -m twine check dist/*

echo "[3/5] Verify built artifacts"
python3 - <<'PY'
from pathlib import Path
from packaging.version import Version
import re
import tomllib

source = Path("fsresourcetree/__init__.py").read_text(encoding="utf-8")
match = re.search(r'^__version__ = "([^"]+)"$', source, re.MULTILINE)
assert match, "package version declaration not found"
version = Version(match.group(1))
metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
assert "version" in metadata.get("dynamic", []), "pyproject.toml must keep dynamic version metadata"
artifacts = list(Path("dist").glob("*"))
assert len(artifacts) == 2, artifacts
assert any(path.name.endswith(".whl") for path in artifacts)
assert any(path.name.endswith(".tar.gz") for path in artifacts)
print(f"Validated version {version} and artifacts: {[path.name for path in artifacts]}")
PY

echo "[4/5] Commit and tag only after successful validation"
git add fsresourcetree/__init__.py
git commit -m "Release $VERSION"
git tag -a "v$VERSION" -m "fsresource-tree $VERSION"

echo "[5/5] Push release and publish to PyPI"
git push origin main
git push origin "v$VERSION"
python3 -m twine upload dist/*

trap - ERR
echo "Published fsresource-tree $VERSION"
