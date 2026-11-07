"""Write the hand-check files for human reviewers.

Outputs in <review-dir>:
- physics-9-10-review.md : one section per chapter, every item with its PDF page, flags and a
  checkbox. Read next to the PDF.
- physics-9-10-review.csv: the same items as rows. Reviewer fills `verdict` (ok / fix / drop),
  `corrected_value` and `reviewer`; apply_review.py writes them back (verified=true).
- topics.md (in the data dir): the topic ID list the bench agent uses.

Usage: python3 pipeline/review.py <data-subject-dir> <review-dir>
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


def main(data_dir: str, review_dir: str) -> None:
    d_dir = Path(data_dir)
    r_dir = Path(review_dir)
    r_dir.mkdir(parents=True, exist_ok=True)
    books = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(d_dir.glob("*-[be]n.json"))]
    md = [
        "# Hand-check: Physics 9-10 (2026 edition), Bangla and English versions",
        "",
        "Every item below was machine-extracted by OCR and is stored with `verified: false`.",
        "Open the PDF at the given page, compare, tick the box, and record the result in the CSV",
        "(`verdict` = ok / fix / drop, `corrected_value` when fixing, `reviewer` = your name).",
        "`agent_checked` means the extraction agent compared the item with the page image or the",
        "other-language book; it is not a human check.",
        "",
        "Priority: rows with flags first, then topics (shared with the bench), then objectives, then exercise counts.",
        "",
    ]
    md += ["## Summary", "", "| Book | Ch | sections | objectives | worked ex. | MCQ/CQ/SQ | agent-checked | verified | flags |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for b in books:
        for ch in b["chapters"]:
            items = [x for k in ("topics", "objectives", "worked_examples", "exercises") for x in b[k] if x["chapter_id"] == ch["id"]]
            c = ch["counts"]
            md.append(
                f"| {b['book']['version']} | {ch['number']} | {c['topics'] + c['subtopics']} | {c['objectives']} | {c['worked_examples']} | "
                f"{c.get('ex_mcq', 0)}/{c.get('ex_cq', 0)}/{c.get('ex_sq', 0)} | {sum(x['review']['agent_checked'] for x in items)} | "
                f"{sum(x['review']['verified'] for x in items)} | {', '.join(ch['review']['flags']) or '—'} |"
            )
    md += ["", "Bangla/English section pairing: see `data/physics-9-10/pairing-report.md`.", ""]
    rows = []
    for b in books:
        bk = b["book"]
        md += [f"## {bk['title']} (`{bk['id']}`)", "", f"PDF: {bk['source']['pdf_urls'][0]} (sha256 {bk['source']['sha256'][:12]}…)", ""]
        for ch in b["chapters"]:
            md += [
                f"### Ch {ch['number']}: {ch['title']}" + (f" ({ch['title_alt']})" if ch.get("title_alt") else ""),
                f"`{ch['id']}` · PDF pp. {ch['pages']['start']['pdf']}-{ch['pages']['end']['pdf']} (printed {ch['pages']['start']['printed']}-{ch['pages']['end']['printed']})"
                + (f" · **flags: {', '.join(ch['review']['flags'])}**" if ch["review"]["flags"] else ""),
                "",
            ]
            rows.append([ch["id"], "chapter", "title", ch["title"], ch["pages"]["start"]["pdf"], ";".join(ch["review"]["flags"]), "yes" if ch["review"]["agent_checked"] else "", "", "", ""])
            md.append("Topics:")
            for t in [t for t in b["topics"] if t["chapter_id"] == ch["id"]]:
                flag = f" ⚠ {', '.join(t['review']['flags'])}" if t["review"]["flags"] else ""
                chk = "" if t.get("concept_key_checked") else " (bn/en not paired)"
                ind = "  " if t["level"] == "subtopic" else ""
                alt = f" ({t['title_alt']})" if t.get("title_alt") else ""
                ac = " (agent-checked on page image)" if t["review"]["agent_checked"] else ""
                md.append(f"{ind}- [ ] {t['number']} {t['title']}{alt} — p.{t['page']['pdf']} `{t['id']}`{flag}{chk}{ac}")
                rows.append([t["id"], "topic", "title", t["title"] + alt, t["page"]["pdf"], ";".join(t["review"]["flags"]), "yes" if t["review"]["agent_checked"] else "", "", "", ""])
            objs = [o for o in b["objectives"] if o["chapter_id"] == ch["id"]]
            md += ["", f"Objectives ({len(objs)}):"]
            for o in objs:
                flag = f" ⚠ {', '.join(o['review']['flags'])}" if o["review"]["flags"] else ""
                ac = " (agent-checked on page image)" if o["review"]["agent_checked"] else ""
                md.append(f"- [ ] o{o['number']:02d} {o['text']} — p.{o['page']['pdf']}{flag}{ac}")
                rows.append([o["id"], "objective", "text", o["text"], o["page"]["pdf"], ";".join(o["review"]["flags"]), "yes" if o["review"]["agent_checked"] else "", "", "", ""])
            c = ch.get("counts", {})
            we = [w for w in b["worked_examples"] if w["chapter_id"] == ch["id"]]
            md += [
                "",
                f"- [ ] Worked examples found: {len(we)} on PDF pages {', '.join(str(w['page']['pdf']) for w in we) or '—'}",
                f"- [ ] Exercise items found: MCQ {c.get('ex_mcq', 0)}, creative {c.get('ex_cq', 0)}, short {c.get('ex_sq', 0)}, numerical {c.get('ex_num', 0)}",
                "",
            ]
            rows.append([ch["id"], "chapter", "counts", json.dumps({**c, "worked_example_pages": [w["page"]["pdf"] for w in we]}), ch["pages"]["end"]["pdf"], "", "", "", "", ""])
        md.append("")
    (r_dir / "physics-9-10-review.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    with (r_dir / "physics-9-10-review.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "type", "field", "extracted_value", "pdf_page", "flags", "agent_checked", "verdict", "corrected_value", "reviewer"])
        w.writerows(rows)

    # topic list for other consumers (bench)
    tl = ["# Physics 9-10 topic IDs (generated; do not edit by hand)", ""]
    for b in books:
        tl += [f"## {b['book']['id']}", "", "| ID | No. | Title | PDF p. | printed p. | bn/en paired |", "| --- | --- | --- | --- | --- | --- |"]
        for t in b["topics"]:
            alt = f" ({t['title_alt']})" if t.get("title_alt") else ""
            tl.append(f"| `{t['id']}` | {t['number']} | {t['title']}{alt} | {t['page']['pdf']} | {t['page']['printed']} | {'yes' if t.get('concept_key_checked') else 'no'} |")
        tl.append("")
    (d_dir / "topics.md").write_text("\n".join(tl) + "\n", encoding="utf-8")
    print(f"review: {len(rows)} rows")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
