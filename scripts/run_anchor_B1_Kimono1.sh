#!/usr/bin/env bash
set -euo pipefail

QP="${1:?Usage: $0 <22|27|32|37>}"
FRAMES="${FRAMES:-64}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENCODER="${VTM_ENCODER:-$ROOT/bin/EncoderAppStatic}"
CFG="${VTM_CFG:-$ROOT/cfg/encoder_randomaccess_vtm.cfg}"
INPUT="${VTM_INPUT:-$ROOT/test_sequence/B1_Kimono1_1920x1080_24.yuv}"
OUT="${VTM_OUTPUT_DIR:-$ROOT/results/B1_Kimono1/QP$QP}"

case "$QP" in 22|27|32|37) ;; *) echo "Unsupported QP: $QP" >&2; exit 2;; esac
for file in "$ENCODER" "$CFG" "$INPUT"; do
  test -e "$file" || { echo "Missing required file: $file" >&2; exit 1; }
done
test -x "$ENCODER" || chmod +x "$ENCODER"
mkdir -p "$OUT"

"$ENCODER" -c "$CFG" -i "$INPUT"   -wdt 1920 -hgt 1080 -fr 24 -f "$FRAMES" -q "$QP"   --InputBitDepth=8 --InputChromaFormat=420 --MTS=1 --LFNST=1   -b "$OUT/B1_Kimono1_QP$QP.vvc" 2>&1 | tee "$OUT/B1_Kimono1_QP$QP.log"
