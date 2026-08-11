#!/usr/bin/env bash
set -euo pipefail

SEQUENCE="${1:?Usage: $0 <D1_RaceHorses|D2_BQSquare|D3_BlowingBubbles> <22|27|32|37> [frames]}"
QP="${2:?Usage: $0 <sequence> <22|27|32|37> [frames]}"
FRAMES="${3:-64}"

case "$QP" in
  22|27|32|37) ;;
  *) echo "Unsupported QP: $QP" >&2; exit 2 ;;
esac

case "$SEQUENCE" in
  D1_RaceHorses)
    CFG_NAME="RaceHorses.cfg"
    YUV_NAME="D1_RaceHorses_416x240_30.yuv"
    ;;
  D2_BQSquare)
    CFG_NAME="BQSquare.cfg"
    YUV_NAME="D2_BQSquare_416x240_60.yuv"
    ;;
  D3_BlowingBubbles)
    CFG_NAME="BlowingBubbles.cfg"
    YUV_NAME="D3_BlowingBubbles_416x240_50.yuv"
    ;;
  *) echo "Unsupported Class-D sequence: $SEQUENCE" >&2; exit 2 ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENCODER="${VTM_ENCODER:-$ROOT_DIR/bin/EncoderAppStatic}"
INPUT_YUV="${CLASS_D_YUV:-$ROOT_DIR/Test_Sequences/$YUV_NAME}"
RESULT_DIR="${RESULT_DIR:-$ROOT_DIR/results/Class_D/$SEQUENCE/QP${QP}}"
mkdir -p "$RESULT_DIR"

BITSTREAM="$RESULT_DIR/${SEQUENCE}_QP${QP}.bin"
VTM_LOG="$RESULT_DIR/${SEQUENCE}_QP${QP}_vtm.log"
SPARSITY_CSV="$RESULT_DIR/${SEQUENCE}_QP${QP}_measured_sparsity.csv"
CDSATM_SUMMARY="$RESULT_DIR/${SEQUENCE}_QP${QP}_cdsatm_summary.txt"
RUN_SUMMARY="$RESULT_DIR/${SEQUENCE}_QP${QP}_summary.txt"

test -x "$ENCODER" || { echo "Encoder not executable: $ENCODER" >&2; exit 3; }
test -f "$INPUT_YUV" || { echo "Input sequence not found: $INPUT_YUV" >&2; exit 4; }

echo "Starting measured CD-SATM run: $SEQUENCE | Frames: $FRAMES | QP: $QP"
CDSATM_SPARSITY_LOG="$SPARSITY_CSV" "$ENCODER" \
  -c "$ROOT_DIR/cfg/encoder_randomaccess_vtm.cfg" \
  -c "$ROOT_DIR/cfg/per-sequence/$CFG_NAME" \
  --InputFile="$INPUT_YUV" \
  -f "$FRAMES" -q "$QP" --MTS=1 --LFNST=1 -b "$BITSTREAM" \
  2>&1 | tee "$VTM_LOG"

test -s "$SPARSITY_CSV" || { echo "Measured sparsity CSV was not produced" >&2; exit 5; }
python3 "$ROOT_DIR/cdsatm_measured_analyzer.py" \
  --csv "$SPARSITY_CSV" --seq "$SEQUENCE" --qp "$QP" --frames "$FRAMES" \
  | tee "$CDSATM_SUMMARY"

{
  echo "$SEQUENCE proposed measured run | QP $QP | $FRAMES frames"
  echo
  echo "VTM bitrate / PSNR summary:"
  grep -E '^(SUMMARY|a[[:space:]]|Total Time)' "$VTM_LOG" || true
  cat "$CDSATM_SUMMARY"
} | tee "$RUN_SUMMARY"

echo "Completed $SEQUENCE QP $QP. Results: $RESULT_DIR"
