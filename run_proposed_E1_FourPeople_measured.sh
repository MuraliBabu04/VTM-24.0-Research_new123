#!/usr/bin/env bash
set -euo pipefail

QP="${1:?Usage: $0 <22|27|32|37> [frames]}"
FRAMES="${2:-64}"
case "$QP" in
  22|27|32|37) ;;
  *) echo "Unsupported QP: $QP" >&2; exit 2 ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENCODER="${VTM_ENCODER:-$ROOT_DIR/bin/EncoderAppStatic}"
INPUT_YUV="${FOURPEOPLE_YUV:-$ROOT_DIR/Test_Sequences/E1_FourPeople_1280x720_60.yuv}"
RESULT_DIR="${RESULT_DIR:-$ROOT_DIR/results/E1_FourPeople/QP${QP}}"
mkdir -p "$RESULT_DIR"

BITSTREAM="$RESULT_DIR/E1_FourPeople_QP${QP}.bin"
VTM_LOG="$RESULT_DIR/E1_FourPeople_QP${QP}_vtm.log"
SPARSITY_CSV="$RESULT_DIR/E1_FourPeople_QP${QP}_measured_sparsity.csv"
CDSATM_SUMMARY="$RESULT_DIR/E1_FourPeople_QP${QP}_cdsatm_summary.txt"
RUN_SUMMARY="$RESULT_DIR/E1_FourPeople_QP${QP}_summary.txt"

test -x "$ENCODER" || { echo "Encoder not executable: $ENCODER" >&2; exit 3; }
test -f "$INPUT_YUV" || { echo "Input sequence not found: $INPUT_YUV" >&2; exit 4; }

echo "Starting measured CD-SATM run: E1_FourPeople | Frames: $FRAMES | QP: $QP"
CDSATM_SPARSITY_LOG="$SPARSITY_CSV" "$ENCODER" \
  -c "$ROOT_DIR/cfg/encoder_randomaccess_vtm.cfg" \
  -c "$ROOT_DIR/cfg/per-sequence/FourPeople.cfg" \
  --InputFile="$INPUT_YUV" \
  -f "$FRAMES" -q "$QP" --MTS=1 --LFNST=1 -b "$BITSTREAM" \
  2>&1 | tee "$VTM_LOG"

test -s "$SPARSITY_CSV" || { echo "Measured sparsity CSV was not produced" >&2; exit 5; }
python3 "$ROOT_DIR/cdsatm_measured_analyzer.py" \
  --csv "$SPARSITY_CSV" --seq E1_FourPeople --qp "$QP" --frames "$FRAMES" \
  | tee "$CDSATM_SUMMARY"

{
  echo "E1_FourPeople proposed measured run | QP $QP | $FRAMES frames"
  echo
  echo "VTM bitrate / PSNR summary:"
  grep -E '^(SUMMARY|a[[:space:]]|Total Time)' "$VTM_LOG" || true
  cat "$CDSATM_SUMMARY"
} | tee "$RUN_SUMMARY"

echo "Completed QP $QP. Results: $RESULT_DIR"
