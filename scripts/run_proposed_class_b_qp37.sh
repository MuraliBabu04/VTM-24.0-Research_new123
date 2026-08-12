#!/usr/bin/env bash
set -euo pipefail

SEQUENCE="${1:?Usage: $0 <B1_Kimono1|B2_ParkScene|B3_Cactus> [frames]}"
QP=37
FRAMES="${2:-64}"

case "$SEQUENCE" in
  B1_Kimono1)
    CFG_NAME="Kimono.cfg"
    YUV_NAME="B1_Kimono1_1920x1080_24.yuv"
    ;;
  B2_ParkScene)
    CFG_NAME="ParkScene.cfg"
    YUV_NAME="B2_ParkScene_1920x1080_24.yuv"
    ;;
  B3_Cactus)
    CFG_NAME="Cactus.cfg"
    YUV_NAME="B3_Cactus_1920x1080_50.yuv"
    ;;
  *) echo "Unsupported Class-B sequence: $SEQUENCE" >&2; exit 2 ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENCODER="${VTM_ENCODER:-$ROOT_DIR/bin/EncoderAppStatic}"
INPUT_YUV="${CLASS_B_YUV:-$ROOT_DIR/Test_Sequences/$YUV_NAME}"
ANALYZER="${CDSATM_ANALYZER:-$ROOT_DIR/cdsatm_measured_analyzer.py}"
RESULT_DIR="${RESULT_DIR:-$ROOT_DIR/results/Class_B/$SEQUENCE/QP37}"
mkdir -p "$RESULT_DIR"

BITSTREAM="$RESULT_DIR/${SEQUENCE}_QP37.bin"
VTM_LOG="$RESULT_DIR/${SEQUENCE}_QP37_vtm.log"
SPARSITY_CSV="$RESULT_DIR/${SEQUENCE}_QP37_measured_sparsity.csv"
CDSATM_LOG="$RESULT_DIR/${SEQUENCE}_QP37_cdsatm_summary.txt"
RUN_SUMMARY="$RESULT_DIR/${SEQUENCE}_QP37_summary.txt"

test -x "$ENCODER" || chmod +x "$ENCODER"
test -x "$ENCODER" || { echo "Encoder not executable: $ENCODER" >&2; exit 3; }
test -f "$INPUT_YUV" || { echo "Input sequence not found: $INPUT_YUV" >&2; exit 4; }
test -f "$ANALYZER" || { echo "Analyzer not found: $ANALYZER" >&2; exit 5; }

echo "Starting measured CD-SATM run: $SEQUENCE | Frames: $FRAMES | QP: 37"
CDSATM_SPARSITY_LOG="$SPARSITY_CSV" "$ENCODER" \
  -c "$ROOT_DIR/cfg/encoder_randomaccess_vtm.cfg" \
  -c "$ROOT_DIR/cfg/per-sequence/$CFG_NAME" \
  --InputFile="$INPUT_YUV" \
  -f "$FRAMES" -q "$QP" --MTS=1 --LFNST=1 -b "$BITSTREAM" \
  2>&1 | tee "$VTM_LOG"

test -s "$SPARSITY_CSV" || { echo "Measured sparsity CSV was not produced" >&2; exit 6; }
python3 "$ANALYZER" \
  --csv "$SPARSITY_CSV" --seq "$SEQUENCE" --qp "$QP" --frames "$FRAMES" \
  | tee "$CDSATM_LOG"

{
  echo "$SEQUENCE proposed measured run | QP 37 | $FRAMES frames"
  echo "MTS: 1"
  echo "LFNST: 1"
  echo
  echo "VTM bitrate / PSNR summary:"
  grep -E '^(SUMMARY|a[[:space:]]|Total Time)' "$VTM_LOG" || true
  echo
  echo "Measured CD-SATM hardware metrics:"
  cat "$CDSATM_LOG"
} | tee "$RUN_SUMMARY"

echo "Completed $SEQUENCE QP37. Results: $RESULT_DIR"
