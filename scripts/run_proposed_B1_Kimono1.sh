#!/usr/bin/env bash
set -euo pipefail

QP="${1:?Usage: $0 <22|27|32|37>}"
FRAMES="${FRAMES:-64}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SIMULATOR="${CDSATM_SIMULATOR:-$ROOT/cdsatm_des_simulator.py}"
OUT="${PROPOSED_OUTPUT_DIR:-$ROOT/results/proposed/B1_Kimono1/QP$QP}"
CODEC_OUT="$OUT/vtm_reference"
HARDWARE_OUT="$OUT/cdsatm_hardware"

case "$QP" in
  22|27|32|37) ;;
  *) echo "Unsupported QP: $QP" >&2; exit 2 ;;
esac

test -f "$SIMULATOR" || {
  echo "Missing required simulator: $SIMULATOR" >&2
  exit 1
}

mkdir -p "$CODEC_OUT" "$HARDWARE_OUT"

echo "Running standard VTM coding reference for the bit-exact CD-SATM methodology."
echo "QP=$QP Frames=$FRAMES MTS=1 LFNST=1"
VTM_OUTPUT_DIR="$CODEC_OUT" \
  "$ROOT/scripts/run_anchor_B1_Kimono1.sh" "$QP"

python3 "$SIMULATOR" \
  --seq B1_Kimono1 \
  --qp "$QP" \
  --frames "$FRAMES" \
  --mts 1 \
  --lfnst 1 \
  2>&1 | tee "$HARDWARE_OUT/B1_Kimono1_QP$QP_power_latency.log"

{
  echo "B1 Kimono1 Proposed CD-SATM methodology"
  echo "QP: $QP"
  echo "Frames: $FRAMES"
  echo "MTS: 1"
  echo "LFNST: 1"
  echo
  echo "Codec metrics below are measured using standard VTM as the bit-exact reference."
  echo "Hardware metrics below are produced by the CD-SATM DES model."
  echo
  grep -E "SUMMARY|Total Frames|^[[:space:]]*[0-9]+[[:space:]]+a[[:space:]]" \
    "$CODEC_OUT/B1_Kimono1_QP$QP.log" || true
  echo
  cat "$HARDWARE_OUT/B1_Kimono1_QP$QP_power_latency.log"
} | tee "$OUT/B1_Kimono1_QP$QP_combined_summary.txt"
