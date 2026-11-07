#!/usr/bin/env bash
# Full pipeline for one subject (v0.1: Physics 9-10, bn + en). Steps:
#  1. OCR every PDF page   (ocr.sh; Tesseract 5, tessdata_best ben+eng models for the Bangla book)
#  2. fix Bangla Unicode / conjunct errors (fix_bangla.py, used by structure.py)
#  3. structure into nctb-data JSON (structure.py + books/*.json + books/*.corrections.json)
#  4. pair the two versions, write the manifest (pair.py) and the hand-check files (review.py)
#
# Environment:
#   OCR_DIR            required: holds physics/ (bn) and physics-en/ (en) folders of pNNN.txt
#   NCTB_SHARED_DATA   output data dir (default: ../nctb-shared/data next to this repo)
#   REVIEW_DIR         review sheet dir (default: $NCTB_SHARED_DATA/../review)
#   PDF_DIR            optional: if set, step 1 runs first (expects physics.pdf, physics-en.pdf)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
: "${OCR_DIR:?set OCR_DIR to the folder that holds physics/ and physics-en/ OCR text}"
DATA=${NCTB_SHARED_DATA:-$HERE/../../nctb-shared/data}
REVIEW=${REVIEW_DIR:-$DATA/../review}
OUT=$DATA/physics-9-10
mkdir -p "$OUT" "$REVIEW"

if [ -n "${PDF_DIR:-}" ]; then
  "$HERE/ocr.sh" "$PDF_DIR/physics-en.pdf" "$OCR_DIR/physics-en" eng
  "$HERE/ocr.sh" "$PDF_DIR/physics.pdf" "$OCR_DIR/physics" ben+eng
fi

# English first: its Latin section numbers OCR reliably and are used to repair Bangla ones.
python3 "$HERE/structure.py" "$HERE/books/physics-9-10-en.json" "$OCR_DIR/physics-en" "$OUT/physics-9-10-en.json"
python3 "$HERE/structure.py" "$HERE/books/physics-9-10-bn.json" "$OCR_DIR/physics" "$OUT/physics-9-10-bn.json" "$OUT/physics-9-10-en.json"
python3 "$HERE/pair.py" "$OUT/physics-9-10-bn.json" "$OUT/physics-9-10-en.json"
python3 "$HERE/review.py" "$OUT" "$REVIEW"
