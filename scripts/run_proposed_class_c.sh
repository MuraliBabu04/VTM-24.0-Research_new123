#!/usr/bin/env bash
set -euo pipefail

SEQUENCE="${1:?Usage: $0 <C1_RaceHorses|C2_BQMall|C3_PartyScene> <22|27|32|37> [frames]}"
QP="${2:?Usage: $0 <sequence> <22|27|32|37> [frames]}"
FRAMES="${3:-96}"

case "$QP" in
  22|27|32|37) ;;
  *) echo "Unsupported QP: $QP" >&2; exit 2 ;;
esac

case "$SEQUENCE" in
  C1_RaceHorses)
    CFG_NAME="RaceHorsesC.cfg"
    YUV_NAME="C1_RaceHorses_832x480_30.yuv"
    ;;
  C2_BQMall)
    CFG_NAME="BQMall.cfg"
    YUV_NAME="C2_BQMall_832x480_60.yuv"
    ;;
  C3_PartyScene)
    CFG_NAME="PartyScene.cfg"
    YUV_NAME="C3_PartyScene_832x480_50.yuv"
    ;;
  *) echo "Unsupported Class-C sequence: $SEQUENCE" >&2; exit 2 ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENCODER="${VTM_ENCODER:-$ROOT_DIR/bin/EncoderAppStatic}"
INPUT_YUV="${CLASS_C_YUV:-$ROOT_DIR/Test_Sequences/$YUV_NAME}"
ANALYZER="${CDSATM_ANALYZER:-$ROOT_DIR/cdsatm_measured_analyzer.py}"
RESULT_DIR="${RESULT_DIR:-$ROOT_DIR/results/Class_C/$SEQUENCE/QP${QP}}"
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

echo "Starting CD-SATM run: $SEQUENCE | Frames: $FRAMES | QP: $QP"
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
  echo "$SEQUENCE proposed CD-SATM run | QP $QP | $FRAMES frames"
  echo "MTS: 1"
  echo "LFNST: 1"
  echo
  echo "VTM bitrate / PSNR summary:"
  grep -E '^(SUMMARY|a[[:space:]]|Total Time)' "$VTM_LOG" || true
  echo
  echo "CD-SATM hardware metrics:"
  cat "$CDSATM_LOG"
} | tee "$RUN_SUMMARY"

echo "Completed $SEQUENCE QP $QP. Results: $RESULT_DIR"
