#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIX_BOOTSTRAP="${VIX_BOOTSTRAP:-/home/zty/Vix-lang/bootstrap}"
VIXC0="${VIXC0:-$VIX_BOOTSTRAP/vixc0}"

mkdir -p "$ROOT/build"
(
  cd "$VIX_BOOTSTRAP"
  "$VIXC0" -exe "$ROOT/src/main.vix" -o "$ROOT/build/very-vix"
)

printf '%s\n' "$ROOT/build/very-vix"
