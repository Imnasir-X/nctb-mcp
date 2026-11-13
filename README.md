# nctb-mcp

An MCP server that lets any AI assistant look up the Bangladesh NCTB curriculum by chapter, section and learning
objective, with the official PDF page for everything it returns. Works offline (`npx`), read-only, no API keys.

> **v0.1 scope:** Class 9-10 (SSC) **Physics**, 2026 edition, **Bangla version and English version**.
> Structure, pages and objective lines are released as the **nctb-data@0.1.0** dataset: chapter titles and start
> pages are hand-checked against the printed contents pages; everything else is machine-extracted
> (`verified: false`) pending human review. See [Data status](#data-status).

```text
You:    Give me Class 9 physics chapter 3.
Claude: (calls get_topic {chapter: 3})
        Chapter 3, বল (Force), PDF pages 67-102 (printed 62-97): 9 sections, 3.1 জড়তা এবং বলের ধারণা:
        নিউটনের প্রথম গতি সূত্র … 3.9 ঘর্ষণ বল, plus 12 subsections. 12 learning objectives,
        6 worked examples, 7 MCQ + 2 creative + 4 short exercise items. Read it in the official NCTB PDF from page 67.
```

## Use it from Claude Desktop, Cursor or any MCP client

```json
{
  "mcpServers": {
    "nctb": { "command": "npx", "args": ["-y", "nctb-mcp"] }
  }
}
```

- **Claude Desktop:** Settings › Developer › Edit Config (`claude_desktop_config.json`), paste the block, restart.
- **Cursor:** `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project), same block.
- **From a local checkout (if `npx` cannot find the package yet):**
  `git clone https://github.com/Imnasir-X/nctb-mcp && cd nctb-mcp && pnpm install && pnpm build`, then use
  `"command": "node", "args": ["/path/to/nctb-mcp/dist/cli.js"]`.

## Tools

Every response is small JSON with IDs for drill-down, the source **PDF page** (and printed page), and the
**`verified`** flag.

| Tool                | Input                                                   | Returns                                                                 |
| ------------------- | ------------------------------------------------------- | ----------------------------------------------------------------------- |
| `list_chapters`     | `subject?`, `class?`, `version?`                        | Book info, 13 chapters with IDs, titles, page ranges, topic counts      |
| `get_topic`         | `id`, or `chapter` (+ `topic` like `"3.2"`), `version?` | A chapter with its sections, or a section with subtopics and neighbours |
| `search_curriculum` | `query` (Bangla or English), `version?`, `limit?`       | Matching chapters, sections and objectives                              |
| `get_objectives`    | `id` or `chapter`, `version?`                           | The chapter's learning outcomes ("... পারব" / "be able to ...")         |
| `get_exercises`     | `id` or `chapter`, `kind?` (`mcq`, `cq`, `sq`, `num`)   | Exercise items and worked examples as **pointers** (ID, number, page)   |

Subjects accept English, Bangla or romanised Bangla (`physics`, `পদার্থবিজ্ঞান`, `podartho biggan`). Classes accept
`9`, `10`, `9-10`, `SSC`, `নবম`, `দশম`. Section numbers accept Bangla digits (`"৩.২"`). `version` is `bn`
(default) or `en`; the two versions are separate books with different page numbers.

### Example responses

Real output of the built server (v0.1.0, captured with the MCP Inspector CLI on 2026-11-07).

`get_topic {"chapter": 1, "topic": "1.5"}`

```json
{
  "type": "topic",
  "id": "nctb:phy:c9-10:bn:ch01:t05",
  "number": "1.5",
  "title": "ভৌত রাশি এবং তাদের পরিমাপ",
  "printed_page": 14,
  "pdf_page": 19,
  "verified": false,
  "level": "topic",
  "chapter": {
    "id": "nctb:phy:c9-10:bn:ch01",
    "number": 1,
    "title": "ভৌত রাশি এবং তাদের পরিমাপ"
  },
  "parent_id": null,
  "subtopics": [
    {
      "id": "nctb:phy:c9-10:bn:ch01:t05:s01",
      "number": "1.5.1",
      "title": "পরিমাপের একক",
      "title_alt": "Units of Measurements",
      "printed_page": 15,
      "pdf_page": 20,
      "verified": false
    },
    {
      "id": "nctb:phy:c9-10:bn:ch01:t05:s02",
      "number": "1.5.2",
      "title": "উপসর্গ বা গুণিতক",
      "title_alt": "Prefix",
      "printed_page": 17,
      "pdf_page": 22,
      "verified": false
    },
    {
      "id": "nctb:phy:c9-10:bn:ch01:t05:s03",
      "number": "1.5.3",
      "title": "মাত্রা",
      "title_alt": "Dimension",
      "printed_page": 18,
      "pdf_page": 23,
      "verified": false
    },
    {
      "id": "nctb:phy:c9-10:bn:ch01:t05:s04",
      "number": "1.5.4",
      "title": "বৈজ্ঞানিক প্রতীক ও সংকেত",
      "title_alt": "Scientific Symbols and Notations",
      "printed_page": 19,
      "pdf_page": 24,
      "verified": false
    }
  ],
  "previous_id": "nctb:phy:c9-10:bn:ch01:t04:s03",
  "next_id": "nctb:phy:c9-10:bn:ch01:t05:s01",
  "worked_example_ids": [],
  "source": {
    "book_id": "nctb:phy:c9-10:bn",
    "printed_page": 14,
    "pdf_page": 19,
    "pdf_urls": [
      "https://drive.google.com/file/d/13P5E08HcNbpALj8-aC-RUCy0d3iwodet/view",
      "https://drive.egovcloud.gov.bd/index.php/s/KOdI1T0gyhPiFRz"
    ],
    "official_listing_url": "https://nctb.gov.bd/pages/static-pages/695b99afc4774958d7b70612",
    "edition": 2026
  },
  "notice": "Structure, IDs, objectives and page pointers only. Textbook content belongs to NCTB (all rights reserved); open the official PDF page for the text. Items are machine-extracted (OCR) and verified=false until a human checks them."
}
```

`search_curriculum {"query": "momentum", "version": "en", "limit": 3}`

```json
{
  "query": "momentum",
  "hits": [
    {
      "id": "nctb:phy:c9-10:en:ch03:t04",
      "type": "topic",
      "number": "3.4",
      "title": "Momentum",
      "chapter_id": "nctb:phy:c9-10:en:ch03",
      "version": "en",
      "printed_page": 70,
      "pdf_page": 75,
      "verified": false
    },
    {
      "id": "nctb:phy:c9-10:en:ch03:t05:s01",
      "type": "topic",
      "number": "3.5.1",
      "title": "Conservation of Momentum and Energy",
      "chapter_id": "nctb:phy:c9-10:en:ch03",
      "version": "en",
      "printed_page": 71,
      "pdf_page": 76,
      "verified": false
    },
    {
      "id": "nctb:phy:c9-10:en:ch03:o08",
      "type": "objective",
      "title": "explain the conservation laws of momentum and collision.",
      "chapter_id": "nctb:phy:c9-10:en:ch03",
      "version": "en",
      "printed_page": 62,
      "pdf_page": 67,
      "verified": false
    }
  ]
}
```

An unknown ID returns `isError: true` with
`{"error": "Unknown ID nctb:phy:c9-10:bn:ch99", "hint": "Use list_chapters or search_curriculum to get valid IDs."}`.

## IDs

`nctb:<subject>:<class>:<version>:ch<NN>[:t<NN>[:s<NN>] | :o<NN> | :we<NN> | :ex:<kind><NN>]`, e.g.
`nctb:phy:c9-10:bn:ch03:t02` = Physics, Classes 9-10, Bangla version, chapter 3, section 3.2. Topic numbers are the
book's own section numbers. Full scheme: [IDS.md](IDS.md). The same IDs are used by the BanglaEdu Bench.

## What is in the data, and what is not

| Shipped (`data/*.json`)                                           | Not shipped                             |
| ----------------------------------------------------------------- | --------------------------------------- |
| Chapter and section numbers and headings (Bangla + English terms) | Body text of the books                  |
| Chapter learning-objective lines                                  | Worked-example questions or solutions   |
| Printed page and PDF page of every item                           | Exercise / MCQ / creative-question text |
| Counts and positions of worked examples and exercise items        | Board exam questions                    |
| Source PDF URLs, file name, SHA-256, size, edition history        | Any OCR'd page text                     |

The NCTB textbooks are © NCTB, "[All rights reserved by the Publisher]". The PDFs are free from NCTB; this package
points to them instead of copying them. See [DATA_LICENSE.md](DATA_LICENSE.md).

## Data provenance

| Book                           | Official file                                                              | SHA-256 (first 12) | PDF pages | Text layer |
| ------------------------------ | -------------------------------------------------------------------------- | ------------------ | --------- | ---------- |
| পদার্থবিজ্ঞান (Bangla version) | `Secondary (BV)-2026_Class 9-10_Physics_compressed.pdf`, 106,445,726 bytes | `a07b3b394430`     | 366       | none       |
| Physics (English version)      | `Physics  9, com _compressed.pdf`, 52,876,931 bytes                        | `914ad6f4c87d`     | 366       | ~20 pages  |

Both were downloaded on 2026-11-07 from the links on NCTB's page "২০২৬ শিক্ষাবর্ষের মাধ্যমিক স্তরের নবম-দশম শ্রেণির
পাঠ্যপুস্তক" (https://nctb.gov.bd/pages/static-pages/695b99afc4774958d7b70612). The Google Drive and
egovcloud mirrors NCTB links serve files of identical size.

Pipeline (`pipeline/`, Python + Tesseract 5):

1. **OCR** every page (`ocr.sh <pdf> <out-dir> <langs> [dpi]`; resumable, `JOBS`/`TESSDATA_PREFIX` from the
   environment): the PDFs are scanned images, so there is no text to extract directly.
   Bangla book: `ben+eng` tessdata_best at 200 dpi. English book: `eng` at 150 dpi.
   Run everything with `OCR_DIR=<ocr> [PDF_DIR=<pdfs>] pipeline/run.sh`.
2. **Fix Bangla Unicode and conjuncts** (`fix_bangla.py`): NFC, one form for য়/ড়/ঢ়, stray zero-width characters,
   `|` → `।`, and a reviewed word list for OCR conjunct errors (ভোত→ভৌত, যন্দ্র→যন্ত্র, ত্রটি→ত্রুটি, ধুবক→ধ্রুবক …).
   Legacy Bijoy/SutonnyMJ text is detected and reported, never returned.
3. **Structure** (`structure.py`): chapter list hand-transcribed from the printed contents page; sections from
   numbered headings; objectives from the chapter-opening list; worked examples from "প্রশ্ন:/Question:" inside
   example boxes; exercise items from the "নমুনা প্রশ্ন / Sample Questions" section. Running headers and footers removed.
4. **Cross-check** (`pair.py`): the English term printed in each Bangla heading is matched against the English
   book's heading with the same number. Agreement sets `concept_key_checked`.
5. **Agent corrections** (`books/*.corrections.json`): fixes made after looking at the page image (OCR-garbled
   headings and objectives, headings whose number OCR could not read, merged bullets). Each carries its reason and
   page and sets `agent_checked: true`; none sets `verified`. Real differences between the two printed books are
   recorded in `books/physics-9-10.pairing.json`.
6. **Hand-check** (`review.py`, `apply_review.py`): a review sheet and CSV; only a named human can set `verified: true`.

## Data status

Coverage per chapter, Bangla / English (sections / objectives / worked examples / MCQ-creative-short items):

| Ch  | Bangla title                | bn                   | en                   |
| --- | --------------------------- | -------------------- | -------------------- |
| 1   | ভৌত রাশি এবং তাদের পরিমাপ   | 22 / 13 / 3 / 6-2-4  | 22 / 13 / 3 / 6-2-4  |
| 2   | গতি                         | 8 / 7 / 8 / 5-2-4    | 8 / 7 / 8 / 5-2-4    |
| 3   | বল                          | 21 / 12 / 6 / 7-2-4  | 21 / 12 / 6 / 7-2-4  |
| 4   | কাজ, ক্ষমতা ও শক্তি         | 15 / 11 / 9 / 6-2-4  | 15 / 11 / 9 / 6-2-4  |
| 5   | পদার্থের অবস্থা ও চাপ       | 14 / 17 / 14 / 5-2-4 | 14 / 17 / 14 / 5-2-4 |
| 6   | বস্তুর ওপর তাপের প্রভাব     | 12 / 17 / 11 / 5-2-4 | 12 / 17 / 11 / 5-2-4 |
| 7   | তরঙ্গ ও শব্দ                | 11 / 9 / 7 / 5-3-4   | 11 / 10 / 7 / 5-3-4  |
| 8   | আলোর প্রতিফলন               | 17 / 10 / 10 / 5-2-4 | 17 / 10 / 10 / 5-2-4 |
| 9   | আলোর প্রতিসরণ               | 15 / 8 / 7 / 5-1-4   | 15 / 8 / 7 / 5-1-4   |
| 10  | স্থির বিদ্যুৎ               | 16 / 10 / 9 / 5-2-4  | 16 / 10 / 9 / 5-2-4  |
| 11  | চল বিদ্যুৎ                  | 16 / 17 / 9 / 6-2-4  | 16 / 17 / 9 / 6-2-4  |
| 12  | বিদ্যুতের চৌম্বক ক্রিয়া    | 9 / 7 / 4 / 5-2-4    | 9 / 7 / 4 / 5-2-4    |
| 13  | তেজস্ক্রিয়তা ও ইলেকট্রনিকস | 14 / 5 / 1 / 4-1-4   | 14 / 5 / 1 / 4-1-4   |

- Both books: 13 chapters, 190 sections, 98 worked-example pointers, 146 exercise-item pointers; 143 (bn) and 144 (en)
  objectives. The one count difference is in the printed books themselves (ch. 7: the English book lists one more
  outcome), confirmed on the page images.
- Section numbering differs in two places in the printed books (en skips 8.2.2 and 8.8.4), so bn 8.2.2/8.8.4
  correspond to en 8.2.3/8.8.5.
- Chapter titles and start pages: checked by eye against both contents pages.
- Sections, objectives and counts: OCR + automatic bn/en cross-checks + agent corrections on page images
  (`agent_checked`). Remaining issues are listed per item in `review.flags` and in the review sheet.
- `verified: true`: **0 items**. Nothing has been human-verified yet.

## Develop

```bash
pnpm install
pnpm test          # vitest: tool behaviour + data invariants + JSON Schema
pnpm lint && pnpm format:check
pnpm build && node dist/cli.js --version
pnpm inspect       # MCP Inspector UI
npx @modelcontextprotocol/inspector --cli node dist/cli.js --method tools/list
```

Data lives in `../nctb-shared/data` during development; `pnpm sync-data` copies it into `data/`, which is what the
npm package ships.

## Publishing decisions

Three decisions blocked the npm release; all three are now made and recorded in
[docs/OWNERS_DECISIONS.md](docs/OWNERS_DECISIONS.md) with follow-ups:

1. Shipping the books' headings and learning-objective lines is accepted as short factual quotation that points
   to the official text; a permission letter to NCTB remains a follow-up, and any NCTB request is honoured
   immediately.
2. The metadata compilation is licensed **CC BY 4.0**; the textbook text and images remain © NCTB and are not
   licensed here. Code stays MIT.
3. The npm release (`nctb-mcp@0.1.0`) is prepared; the maintainer publishes it by running the Release workflow
   after adding the NPM_TOKEN secret.

## Licence

Code: MIT. NCTB textbook content belongs to NCTB and is not covered by the MIT licence. Not affiliated with NCTB.
