# Changelog

## 0.1.0 (2026-11-07)

- First version: Class 9-10 Physics (2026 edition), Bangla and English versions. Tools: list_chapters, get_topic,
  search_curriculum, get_objectives, get_exercises. Data tag nctb-data@0.1.0, all items verified=false.
- Full coverage of both books: 13 chapters, 190 sections each; 143 (bn) / 144 (en) objectives; 98 worked-example and
  146 exercise-item pointers each. Agent corrections from page images are marked agent_checked.
- Pipeline: `ocr.sh` takes the PDF, output dir and languages as arguments (no fixed paths); `run.sh` reads `OCR_DIR`.
