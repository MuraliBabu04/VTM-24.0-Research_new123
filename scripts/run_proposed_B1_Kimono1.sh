#!/usr/bin/env bash
set -euo pipefail

QP="${1:?Usage: $0 <22|27|32|37>}"
FRAMES="${FRAMES:-64}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SIMULATOR="${CDSATM_SIMULATOR:-$ROOT/cdsatm_des_simulator.py}"
OUT="${PROPOSED_OUTPUT_DIR:-$ROOT/results/proposed/B1_Kimono1/QP$QP}"

case "$QP" in
  22|27|32|37) ;;
  *) echo "Unsupported QP: $QP" >&2; exit 2 ;;
esac

test -f "$SIMULATOR" || {
  echo "Missing required simulator: $SIMULATOR" >&2
  exit 1
}

mkdir -p "$OUT"
python3 "$SIMULATOR"   --seq B1_Kimono1   --qp "$QP"   --frames "$FRAMES"   --mts 1   --lfnst 1   2>&1 | tee "$OUT/B1_Kimono1_QP$QP.log"

if [ -f "$ROOT/cdsatm_simulation_results.html" ]; then
  cp "$ROOT/cdsatm_simulation_results.html" "$OUT/B1_Kimono1_QP$QP.html"
fi
