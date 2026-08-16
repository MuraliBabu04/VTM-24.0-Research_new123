#!/usr/bin/env bash
set -euo pipefail

QP="${1:?Usage: $0 <22|27|32|37> [frames]}"
FRAMES="${2:-32}"

case "$QP" in
  22|27|32|37) ;;
  *) echo "Unsupported A1 Tango QP: $QP" >&2; exit 2 ;;
esac

SEQUENCE="A1_Tango"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENCODER="${VTM_ENCODER:-$ROOT_DIR/bin/EncoderAppStatic}"
INPUT_YUV="${A1_TANGO_YUV:-$ROOT_DIR/Test_Sequences/Tango2_3840x2160_60fps_10bit_420.yuv}"
ANALYZER="${CDSATM_ANALYZER:-$ROOT_DIR/cdsatm_measured_analyzer.py}"
RESULT_DIR="${RESULT_DIR:-$ROOT_DIR/results/Class_A1/$SEQUENCE/QP$QP}"
mkdir -p "$RESULT_DIR"

BITSTREAM="$RESULT_DIR/${SEQUENCE}_QP${QP}.bin"
VTM_LOG="$RESULT_DIR/${SEQUENCE}_QP${QP}_vtm.log"
SPARSITY_CSV="$RESULT_DIR/${SEQUENCE}_QP${QP}_measured_sparsity.csv"
CDSATM_LOG="$RESULT_DIR/${SEQUENCE}_QP${QP}_cdsatm_summary.txt"
RUN_SUMMARY="$RESULT_DIR/${SEQUENCE}_QP${QP}_summary.txt"

test -x "$ENCODER" || chmod +x "$ENCODER"
test -x "$ENCODER" || { echo "Encoder not executable: $ENCODER" >&2; exit 3; }
test -f "$INPUT_YUV" || { echo "Input sequence not found: $INPUT_YUV" >&2; exit 4; }
test -f "$ANALYZER" || { echo "Analyzer not found: $ANALYZER" >&2; exit 5; }

echo "Starting measured CD-SATM run: $SEQUENCE | Frames: $FRAMES | QP: $QP"
CDSATM_SPARSITY_LOG="$SPARSITY_CSV" "$ENCODER" \
  -c "$ROOT_DIR/cfg/encoder_randomaccess_vtm.cfg" \
  -c "$ROOT_DIR/cfg/per-sequence/Tango2.cfg" \
  --InputFile="$INPUT_YUV" \
  -f "$FRAMES" -q "$QP" --MTS=1 --LFNST=1 -b "$BITSTREAM" \
  2>&1 | tee "$VTM_LOG"

test -s "$SPARSITY_CSV" || { echo "Measured sparsity CSV was not produced" >&2; exit 6; }
python3 "$ANALYZER" \
  --csv "$SPARSITY_CSV" --seq "$SEQUENCE" --qp "$QP" --frames "$FRAMES" \
  | tee "$CDSATM_LOG"

{
  echo "$SEQUENCE proposed measured run | QP $QP | $FRAMES frames"
  echo "MTS: 1"
  echo "LFNST: 1"
  echo
  echo "VTM bitrate / PSNR summary:"
  grep -E 'SUMMARY|Total Frames|^[[:space:]]*[0-9]+[[:space:]]+a[[:space:]]|Total Time' "$VTM_LOG" || true
  echo
  echo "Measured CD-SATM hardware metrics:"
  sed -n '1,$p' "$CDSATM_LOG"
} | tee "$RUN_SUMMARY"

echo "Completed $SEQUENCE QP$QP. Results: $RESULT_DIR"
