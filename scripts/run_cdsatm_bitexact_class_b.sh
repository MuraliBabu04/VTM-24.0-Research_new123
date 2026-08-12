#!/usr/bin/env bash
set -euo pipefail

SEQUENCE="${1:?Usage: $0 <B1_Kimono1|B2_ParkScene|B3_Cactus> <22|27|32|37> [frames]}"
QP="${2:?Usage: $0 <sequence> <22|27|32|37> [frames]}"
FRAMES="${3:-32}"

case "$QP" in
  22|27|32|37) ;;
  *) echo "Unsupported QP: $QP" >&2; exit 2 ;;
esac

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
DECODER="${VTM_DECODER:-$ROOT_DIR/bin/DecoderAppStatic}"
INPUT_YUV="${CLASS_B_YUV:-$ROOT_DIR/Test_Sequences/$YUV_NAME}"
RESULT_DIR="${RESULT_DIR:-$ROOT_DIR/results/BitExact_Class_B/$SEQUENCE/QP$QP}"
ANALYZER="$ROOT_DIR/scripts/analyze_cdsatm_bitexact.py"
mkdir -p "$RESULT_DIR"

ANCHOR_BITSTREAM="$RESULT_DIR/${SEQUENCE}_QP${QP}_anchor.bin"
PROPOSED_BITSTREAM="$RESULT_DIR/${SEQUENCE}_QP${QP}_cdsatm.bin"
ANCHOR_RECON="$RESULT_DIR/${SEQUENCE}_QP${QP}_anchor_recon.yuv"
PROPOSED_RECON="$RESULT_DIR/${SEQUENCE}_QP${QP}_cdsatm_recon.yuv"
ANCHOR_DECODED="$RESULT_DIR/${SEQUENCE}_QP${QP}_anchor_decoded.yuv"
PROPOSED_DECODED="$RESULT_DIR/${SEQUENCE}_QP${QP}_cdsatm_decoded.yuv"
ANCHOR_LOG="$RESULT_DIR/${SEQUENCE}_QP${QP}_anchor.log"
PROPOSED_LOG="$RESULT_DIR/${SEQUENCE}_QP${QP}_cdsatm.log"
SPARSITY_CSV="$RESULT_DIR/${SEQUENCE}_QP${QP}_sparsity.csv"
VERIFY_CSV="$RESULT_DIR/${SEQUENCE}_QP${QP}_bitexact.csv"
VERIFY_SUMMARY="$RESULT_DIR/${SEQUENCE}_QP${QP}_bitexact_summary.txt"
HASHES="$RESULT_DIR/${SEQUENCE}_QP${QP}_sha256.txt"
RUN_SUMMARY="$RESULT_DIR/${SEQUENCE}_QP${QP}_summary.txt"

test -x "$ENCODER" || chmod +x "$ENCODER"
test -x "$DECODER" || chmod +x "$DECODER"
test -x "$ENCODER" || { echo "Encoder not executable: $ENCODER" >&2; exit 3; }
test -x "$DECODER" || { echo "Decoder not executable: $DECODER" >&2; exit 4; }
test -f "$INPUT_YUV" || { echo "Input sequence not found: $INPUT_YUV" >&2; exit 5; }

COMMON_ARGS=(
  -c "$ROOT_DIR/cfg/encoder_randomaccess_vtm.cfg"
  -c "$ROOT_DIR/cfg/per-sequence/$CFG_NAME"
  --InputFile="$INPUT_YUV"
  -f "$FRAMES"
  -q "$QP"
  --MTS=1
  --LFNST=1
)

echo "Running untouched VTM anchor: $SEQUENCE | QP $QP | $FRAMES frames"
"$ENCODER" "${COMMON_ARGS[@]}" -b "$ANCHOR_BITSTREAM" -o "$ANCHOR_RECON" 2>&1 | tee "$ANCHOR_LOG"

echo "Running integrated CD-SATM zero-skip path with coefficient verification"
CDSATM_ZERO_SKIP=1 \
CDSATM_SPARSITY_LOG="$SPARSITY_CSV" \
CDSATM_VERIFY_LOG="$VERIFY_CSV" \
"$ENCODER" "${COMMON_ARGS[@]}" -b "$PROPOSED_BITSTREAM" -o "$PROPOSED_RECON" \
  2>&1 | tee "$PROPOSED_LOG"

test -s "$SPARSITY_CSV"
test -s "$VERIFY_CSV"
python3 "$ANALYZER" --csv "$VERIFY_CSV" | tee "$VERIFY_SUMMARY"

cmp "$ANCHOR_BITSTREAM" "$PROPOSED_BITSTREAM"
cmp "$ANCHOR_RECON" "$PROPOSED_RECON"
"$DECODER" -b "$ANCHOR_BITSTREAM" -o "$ANCHOR_DECODED"
"$DECODER" -b "$PROPOSED_BITSTREAM" -o "$PROPOSED_DECODED"
cmp "$ANCHOR_DECODED" "$PROPOSED_DECODED"
cmp "$ANCHOR_RECON" "$ANCHOR_DECODED"
cmp "$PROPOSED_RECON" "$PROPOSED_DECODED"

sha256sum \
  "$ANCHOR_BITSTREAM" "$PROPOSED_BITSTREAM" \
  "$ANCHOR_RECON" "$PROPOSED_RECON" \
  "$ANCHOR_DECODED" "$PROPOSED_DECODED" > "$HASHES"

ANCHOR_METRICS="$(grep -E '^[[:space:]]*[0-9]+[[:space:]]+a[[:space:]]+[0-9]' "$ANCHOR_LOG" | tail -n 1)"
PROPOSED_METRICS="$(grep -E '^[[:space:]]*[0-9]+[[:space:]]+a[[:space:]]+[0-9]' "$PROPOSED_LOG" | tail -n 1)"
test -n "$ANCHOR_METRICS"
test "$ANCHOR_METRICS" = "$PROPOSED_METRICS"

{
  echo "$SEQUENCE integrated CD-SATM verification | QP $QP | $FRAMES frames"
  echo "VTM version: 24.0"
  echo "Bitstream identity: PASS"
  echo "Encoder reconstruction identity: PASS"
  echo "Decoder reconstruction identity: PASS"
  echo "Encoder/decoder reconstruction identity: PASS"
  echo
  echo "Anchor and proposed bitrate / PSNR:"
  echo "$ANCHOR_METRICS"
  echo
  cat "$VERIFY_SUMMARY"
  echo
  cat "$HASHES"
} | tee "$RUN_SUMMARY"

rm -f "$ANCHOR_RECON" "$PROPOSED_RECON" "$ANCHOR_DECODED" "$PROPOSED_DECODED"
echo "Completed bit-exact CD-SATM verification: $RESULT_DIR"
