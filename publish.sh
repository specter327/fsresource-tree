#!/bin/bash

# =========================================================
# resourcetree publisher
# Github + PyPi
# =========================================================


set -e


VERSION=$1


if [ -z "$VERSION" ]; then

    echo "Uso:"
    echo "./publish.sh 0.1.1"

    exit 1

fi



echo ""
echo "================================="
echo " Publishing fsresource-tree $VERSION "
echo "================================="
echo ""



# ---------------------------------------------------------
# Actualizar version
# ---------------------------------------------------------

echo "[1/6] Updating version"


sed -i \
"s/version = \".*\"/version = \"$VERSION\"/" \
pyproject.toml



# ---------------------------------------------------------
# Tests
# ---------------------------------------------------------

echo "[2/6] Running tests"

python3 -m pytest



# ---------------------------------------------------------
# Git commit
# ---------------------------------------------------------

echo "[3/6] Commit"


git add .


git commit \
-m "Release $VERSION"



# ---------------------------------------------------------
# Tag
# ---------------------------------------------------------

echo "[4/6] Creating tag"


git tag "v$VERSION"



# ---------------------------------------------------------
# Github
# ---------------------------------------------------------

echo "[5/6] Push Github"


git push origin main


git push origin "v$VERSION"



# ---------------------------------------------------------
# Build
# ---------------------------------------------------------

echo "[6/6] Building package"


rm -rf dist/*


python3 -m build



# ---------------------------------------------------------
# PyPi
# ---------------------------------------------------------

echo ""
echo "Uploading PyPi"
echo ""


python3 -m twine upload dist/*



echo ""
echo "================================="
echo " DONE"
echo " resourcetree $VERSION published"
echo "================================="