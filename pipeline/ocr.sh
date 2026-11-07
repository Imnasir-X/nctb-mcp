#!/usr/bin/env bash
# Step 1 of the pipeline: OCR every page of one textbook PDF into <out-dir>/pNNN.txt.
#
# usage: pipeline/ocr.sh <book.pdf> <out-dir> <tesseract-langs> [dpi]
#   e.g. pipeline/ocr.sh ~/nctb/physics.pdf    ~/nctb/ocr/physics    ben+eng
#        pipeline/ocr.sh ~/nctb/physics-en.pdf ~/nctb/ocr/physics-en eng
#
# Environment (all optional):
#   JOBS            parallel pages (default: number of CPUs)
#   TESSDATA_PREFIX Tesseract model dir; use the tessdata_best ben/eng models for the Bangla book
#   PSM             Tesseract page segmentation mode (default 4: single column of variable sizes)
#   FIRST, LAST     page range (default: whole PDF)
#
# Resumable and safe to run twice at once: pages that already have a non-empty .txt are
# skipped, and a page being worked on is held by a .lock file.
# Needs: pdfinfo + pdftoppm (poppler), tesseract >= 5.
set -euo pipefail

if [ $# -lt 3 ]; then
  sed -n '2,15p' "$0" >&2
  exit 2
fi
PDF=$1
OUT=$2
LANGS=$3
DPI=${4:-200}
JOBS=${JOBS:-$(nproc 2>/dev/null || echo 2)}
PSM=${PSM:-4}
export OMP_THREAD_LIMIT=1

for bin in pdfinfo pdftoppm tesseract; do
  command -v "$bin" >/dev/null || { echo "missing: $bin" >&2; exit 1; }
done
[ -f "$PDF" ] || { echo "no such PDF: $PDF" >&2; exit 1; }
mkdir -p "$OUT"

N=$(pdfinfo "$PDF" | awk '/^Pages/{print $2}')
FIRST=${FIRST:-1}
LAST=${LAST:-$N}

ocr_page() {
  local p=$1 o
  o="$OUT/p$(printf %03d "$p")"
  [ -s "$o.txt" ] && return 0
  # noclobber makes the lock creation atomic
  (set -o noclobber; : >"$o.lock") 2>/dev/null || return 0
  trap 'rm -f "$o.lock" "$o".img-*.png' RETURN
  pdftoppm -f "$p" -l "$p" -r "$DPI" -gray -png "$PDF" "$o.img" >/dev/null 2>&1
  local img
  img=$(ls "$o".img-*.png 2>/dev/null | head -1)
  [ -n "$img" ] || { echo "page $p: render failed" >&2; return 1; }
  tesseract "$img" "$o" -l "$LANGS" --psm "$PSM" >/dev/null 2>&1 || { echo "page $p: tesseract failed" >&2; return 1; }
}
export -f ocr_page
export OUT PDF DPI LANGS PSM

seq "$FIRST" "$LAST" | xargs -P "$JOBS" -I{} bash -c 'ocr_page "$@"' _ {}

missing=0
for p in $(seq "$FIRST" "$LAST"); do
  [ -s "$OUT/p$(printf %03d "$p").txt" ] || missing=$((missing + 1))
done
echo "$PDF: pages $FIRST-$LAST, $missing without text"
[ "$missing" -eq 0 ]
