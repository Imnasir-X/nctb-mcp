# Contributing

- Run `pnpm install`, then `pnpm test`, `pnpm lint`, `pnpm format:check`, `pnpm validate-data`.
- **Data fixes** go through the review CSV (`pipeline/review.py` writes it, `pipeline/apply_review.py` applies it).
  Only a named human reviewer may set `verified: true`. Never invent a chapter or section title: copy it from the PDF.
- Never add textbook body text, worked-example text or exercise text to `data/`.
- IDs are stable (see `IDS.md`). Do not renumber; drop an item instead of reusing its ID.
