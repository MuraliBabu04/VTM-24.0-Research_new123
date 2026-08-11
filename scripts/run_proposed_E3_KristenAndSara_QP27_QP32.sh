#!/usr/bin/env bash
# Linux GitHub Actions runner for E3 KristenAndSara QP27 and QP32.
set -euo pipefail

QP="${1:?Usage: $0 <27|32>}"
FRAMES="${FRAMES:-64}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENCODER="${VTM_ENCODER:-$ROOT/bin/EncoderAppStatic}"
CFG_BASE="${VTM_CFG:-$ROOT/cfg/encoder_randomaccess_vtm.cfg}"
CFG_SEQ="${VTM_SEQ_CFG:-$ROOT/cfg/per-sequence/KristenAndSara.cfg}"
INPUT="${VTM_INPUT:-$ROOT/test_sequence/E3_KristenAndSara_1280x720_60.yuv}"
SIMULATOR="${CDSATM_SIMULATOR:-$ROOT/cdsatm_des_simulator.py}"
OUT="${PROPOSED_OUTPUT_DIR:-$ROOT/results/proposed/E3_KristenAndSara/QP$QP}"
CODEC_OUT="$OUT/vtm_reference"
HARDWARE_OUT="$OUT/cdsatm_hardware"

case "$QP" in
  27|32) ;;
  *) echo "Unsupported QP: $QP; expected 27 or 32." >&2; exit 2 ;;
esac

for file in "$ENCODER" "$CFG_BASE" "$CFG_SEQ" "$INPUT" "$SIMULATOR"; do
  test -e "$file" || { echo "Missing required file: $file" >&2; exit 1; }
done
test -x "$ENCODER" || chmod +x "$ENCODER"
mkdir -p "$CODEC_OUT" "$HARDWARE_OUT"

echo "Running standard VTM coding reference for the bit-exact CD-SATM methodology."
echo "Sequence=E3_KristenAndSara QP=$QP Frames=$FRAMES MTS=1 LFNST=1"

"$ENCODER" \
  -c "$CFG_BASE" \
  -c "$CFG_SEQ" \
  --InputFile="$INPUT" \
  -f "$FRAMES" \
  -q "$QP" \
  --MTS=1 \
  --LFNST=1 \
  -b "$CODEC_OUT/E3_KristenAndSara_QP${QP}.vvc" \
  2>&1 | tee "$CODEC_OUT/E3_KristenAndSara_QP${QP}.log"

python3 "$SIMULATOR" \
  --seq E3_KristenAndSara \
  --qp "$QP" \
  --frames "$FRAMES" \
  --mts 1 \
  --lfnst 1 \
  2>&1 | tee "$HARDWARE_OUT/E3_KristenAndSara_QP${QP}_power_latency.log"

{
  echo "E3 KristenAndSara Proposed CD-SATM methodology"
  echo "QP: $QP"
  echo "Frames: $FRAMES"
  echo "MTS: 1"
  echo "LFNST: 1"
  echo
  echo "Codec metrics below are measured using standard VTM as the bit-exact reference."
  echo "Hardware metrics below are produced by the CD-SATM DES model."
  echo
  grep -E "SUMMARY|Total Frames|^[[:space:]]*[0-9]+[[:space:]]+a[[:space:]]" \
    "$CODEC_OUT/E3_KristenAndSara_QP${QP}.log" || true
  echo
  cat "$HARDWARE_OUT/E3_KristenAndSara_QP${QP}_power_latency.log"
} | tee "$OUT/E3_KristenAndSara_QP${QP}_combined_summary.txt"
