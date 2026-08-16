#!/usr/bin/env bash
# Standard VTM anchor runner for Classes B, C, D and E.
set -euo pipefail

SEQUENCE="${1:?Usage: $0 <sequence> <22|27|32|37> <frames>}"
QP="${2:?Usage: $0 <sequence> <22|27|32|37> <frames>}"
FRAMES="${3:?Usage: $0 <sequence> <22|27|32|37> <frames>}"

case "$QP" in
  22|27|32|37) ;;
  *) echo "Unsupported anchor QP: $QP; expected 22, 27, 32 or 37." >&2; exit 2 ;;
esac

case "$SEQUENCE" in
  A1_Tango)
    CLASS="A1"; CFG_NAME="Tango2.cfg"; YUV_NAME="Tango2_3840x2160_60fps_10bit_420.yuv"
    ;;
  B1_Kimono1)
    CLASS="B"; CFG_NAME="Kimono.cfg"; YUV_NAME="B1_Kimono1_1920x1080_24.yuv"
    ;;
  B2_ParkScene)
    CLASS="B"; CFG_NAME="ParkScene.cfg"; YUV_NAME="B2_ParkScene_1920x1080_24.yuv"
    ;;
  B3_Cactus)
    CLASS="B"; CFG_NAME="Cactus.cfg"; YUV_NAME="B3_Cactus_1920x1080_50.yuv"
    ;;
  C1_RaceHorses)
    CLASS="C"; CFG_NAME="RaceHorsesC.cfg"; YUV_NAME="C1_RaceHorses_832x480_30.yuv"
    ;;
  C2_BQMall)
    CLASS="C"; CFG_NAME="BQMall.cfg"; YUV_NAME="C2_BQMall_832x480_60.yuv"
    ;;
  C3_PartyScene)
    CLASS="C"; CFG_NAME="PartyScene.cfg"; YUV_NAME="C3_PartyScene_832x480_50.yuv"
    ;;
  D1_RaceHorses)
    CLASS="D"; CFG_NAME="RaceHorses.cfg"; YUV_NAME="D1_RaceHorses_416x240_30.yuv"
    ;;
  D2_BQSquare)
    CLASS="D"; CFG_NAME="BQSquare.cfg"; YUV_NAME="D2_BQSquare_416x240_60.yuv"
    ;;
  D3_BlowingBubbles)
    CLASS="D"; CFG_NAME="BlowingBubbles.cfg"; YUV_NAME="D3_BlowingBubbles_416x240_50.yuv"
    ;;
  E1_FourPeople)
    CLASS="E"; CFG_NAME="FourPeople.cfg"; YUV_NAME="E1_FourPeople_1280x720_60.yuv"
    ;;
  E2_Johnny)
    CLASS="E"; CFG_NAME="Johnny.cfg"; YUV_NAME="E2_Johnny_1280x720_60.yuv"
    ;;
  E3_KristenAndSara)
    CLASS="E"; CFG_NAME="KristenAndSara.cfg"; YUV_NAME="E3_KristenAndSara_1280x720_60.yuv"
    ;;
  *)
    echo "Unsupported anchor sequence: $SEQUENCE" >&2
    exit 2
    ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENCODER="${VTM_ENCODER:-$ROOT_DIR/bin/EncoderAppStatic}"
INPUT_YUV="${VTM_INPUT:-$ROOT_DIR/Test_Sequences/$YUV_NAME}"
CFG_BASE="${VTM_CFG:-$ROOT_DIR/cfg/encoder_randomaccess_vtm.cfg}"
CFG_SEQ="$ROOT_DIR/cfg/per-sequence/$CFG_NAME"
RESULT_DIR="${RESULT_DIR:-$ROOT_DIR/results/Anchor/Class_$CLASS/$SEQUENCE/QP$QP}"
BITSTREAM="$RESULT_DIR/${SEQUENCE}_QP${QP}_anchor.bin"
VTM_LOG="$RESULT_DIR/${SEQUENCE}_QP${QP}_anchor.log"
SUMMARY="$RESULT_DIR/${SEQUENCE}_QP${QP}_anchor_summary.txt"

for file in "$ENCODER" "$INPUT_YUV" "$CFG_BASE" "$CFG_SEQ"; do
  test -e "$file" || { echo "Missing required file: $file" >&2; exit 3; }
done
test -x "$ENCODER" || chmod +x "$ENCODER"
mkdir -p "$RESULT_DIR"

echo "Starting VTM anchor: $SEQUENCE | QP $QP | $FRAMES frames"
"$ENCODER" \
  -c "$CFG_BASE" \
  -c "$CFG_SEQ" \
  --InputFile="$INPUT_YUV" \
  -f "$FRAMES" \
  -q "$QP" \
  --MTS=1 \
  --LFNST=1 \
  -b "$BITSTREAM" \
  2>&1 | tee "$VTM_LOG"

{
  echo "VTM Anchor"
  echo "Class: $CLASS"
  echo "Sequence: $SEQUENCE"
  echo "QP: $QP"
  echo "Frames: $FRAMES"
  echo "GOPSize: 32"
  echo "MTS: 1"
  echo "LFNST: 1"
  echo
  grep -E 'SUMMARY|Total Frames|^[[:space:]]*[0-9]+[[:space:]]+a[[:space:]]|^a[[:space:]]|Total Time' "$VTM_LOG" || true
} | tee "$SUMMARY"

echo "Completed VTM anchor: $SEQUENCE QP $QP"
