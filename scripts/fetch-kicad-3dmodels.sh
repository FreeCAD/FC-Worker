#!/bin/sh
# Populate the KiCad 3D library parent directory.
#
# Layout, mounted into FC-Worker at /usr/share/kicad/3dmodels:
#
#   kicad-3dmodels/
#     KICAD_3DMODEL_DIR/          official packages3D checkout
#
# Usage:
#   ./scripts/fetch-kicad-3dmodels.sh [parent]
#   KICAD_3D_REF=10.0.7 ./scripts/fetch-kicad-3dmodels.sh /path/to/kicad-3dmodels

set -eu

PARENT="${1:-${KICAD_3D_LIBRARIES:-./kicad-3dmodels}}"
REF="${KICAD_3D_REF:-10.0.7}"
REPO="${KICAD_3D_REPO:-https://gitlab.com/kicad/libraries/kicad-packages3D.git}"
OFFICIAL="$PARENT/KICAD_3DMODEL_DIR"

mkdir -p "$PARENT"

if [ -d "$OFFICIAL/.git" ]; then
  git -C "$OFFICIAL" rev-parse -q --verify "refs/tags/$REF^{commit}" >/dev/null ||
    git -C "$OFFICIAL" fetch -q --depth 1 origin "refs/tags/$REF:refs/tags/$REF"
  if [ "$(git -C "$OFFICIAL" rev-parse HEAD)" = "$(git -C "$OFFICIAL" rev-parse "refs/tags/$REF^{commit}")" ]; then
    echo "KiCad 3D library $REF already present at $OFFICIAL"
  else
    echo "Updating KiCad 3D library at $OFFICIAL to $REF"
    git -C "$OFFICIAL" checkout -q "$REF"
  fi
elif [ -d "$OFFICIAL" ]; then
  echo "$OFFICIAL exists but is not a git checkout; leaving it as is"
else
  echo "Cloning $REPO ($REF) into $OFFICIAL"
  rm -rf "$OFFICIAL.tmp"
  git -c advice.detachedHead=false clone -q --depth 1 --branch "$REF" "$REPO" "$OFFICIAL.tmp"
  mv "$OFFICIAL.tmp" "$OFFICIAL"
fi

echo "Done. Mount this parent with KICAD_3D_LIBRARIES=$PARENT"
