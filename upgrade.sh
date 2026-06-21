#!/bin/bash


# =========================================================
# resourcetree updater
# Github sync
# =========================================================


set -e



echo ""
echo "Updating resourcetree"
echo ""



# ---------------------------------------------------------
# Obtener rama actual
# ---------------------------------------------------------

BRANCH=$(git branch --show-current)



echo "Branch:"
echo $BRANCH



# ---------------------------------------------------------
# Descargar cambios
# ---------------------------------------------------------

echo ""
echo "Pulling changes..."
echo ""


git fetch origin


git pull origin $BRANCH



# ---------------------------------------------------------
# Reinstalar
# ---------------------------------------------------------

echo ""
echo "Reinstalling package..."
echo ""


pip install -e .



echo ""
echo "Update completed"
echo ""