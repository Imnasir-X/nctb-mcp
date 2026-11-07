"""Link the Bangla and English versions of a book and write the dataset manifest.

For every section number present in both books, compare the English term printed in the
Bangla heading's parentheses (title_alt) with the English book's heading. When they agree
(fuzzy ratio >= 0.6, or the words of one contain the other) both topics get
concept_key_checked = true. Disagreements and one-sided numbers are written to
pairing-report.md for the reviewer.

Usage: python3 pipeline/pair.py <bn.json> <en.json>
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path


def words(s: str) -> str:
    return " ".join(re.findall(r"[a-z]+", s.lower()))


def agree(a: str | None, b: str) -> float:
    if not a:
        return 0.0
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return 0.0
    if wa in wb or wb in wa:
        return 1.0
    return SequenceMatcher(None, wa, wb).ratio()


def main(bn_path: str, en_path: str) -> None:
    bn = json.loads(Path(bn_path).read_text(encoding="utf-8"))
    en = json.loads(Path(en_path).read_text(encoding="utf-8"))
    en_by_num = {t["number"]: t for t in en["topics"]}
    bn_by_num = {t["number"]: t for t in bn["topics"]}
    rows = []
    checked = 0
    for num, tb in bn_by_num.items():
        te = en_by_num.get(num)
        if not te:
            rows.append((num, tb["title"], tb.get("title_alt") or "", "—", "only in bn"))
            continue
        score = agree(tb.get("title_alt"), te["title"])
        ok = score >= 0.6
        tb["concept_key_checked"] = te["concept_key_checked"] = ok
        if ok:
            checked += 1
        elif not tb.get("title_alt"):
            # the Bangla heading prints no English term, so there is nothing to compare automatically
            rows.append((num, tb["title"], "", te["title"], "same number; bn heading has no English term (compare titles by eye)"))
        else:
            rows.append((num, tb["title"], tb.get("title_alt") or "", te["title"], f"English term differs ({score:.2f})"))
    for num, te in en_by_num.items():
        if num not in bn_by_num:
            rows.append((num, "—", "", te["title"], "only in en"))
    for d, p in ((bn, bn_path), (en, en_path)):
        Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    out = Path(bn_path).parent
    rows.sort(key=lambda r: tuple(int(x) for x in r[0].split(".")))
    md = [
        "# bn/en section pairing report",
        "",
        f"Sections paired automatically (concept_key_checked=true): {checked} of {len(bn_by_num)} bn / {len(en_by_num)} en.",
        "Rows below need a reviewer: either the section exists in one book only (often an OCR miss),",
        "or the English term in the Bangla heading does not match the English book's heading.",
        "",
        "| No. | bn title | bn English term | en title | issue |",
        "| --- | --- | --- | --- | --- |",
    ]
    md += [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in rows]
    md += [
        "",
        "## Per-chapter counts, bn vs en",
        "",
        "The two versions are translations of one book, so counts should match. A mismatch points at an",
        "extraction miss in one of them (or a real difference between the books) and needs a look.",
        "",
        "| Ch | objectives bn/en | worked ex. bn/en | MCQ bn/en | creative bn/en | short bn/en |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    # Differences confirmed on the page images to be real differences between the printed books
    # (pipeline/books/<subject>.pairing.json). They are flagged as such instead of as a likely miss.
    subj = Path(bn_path).name.rsplit("-", 1)[0]
    conf_path = Path(__file__).parent / "books" / f"{subj}.pairing.json"
    confirmed = json.loads(conf_path.read_text(encoding="utf-8")).get("confirmed_count_differences", {}) if conf_path.exists() else {}
    notes = []
    for cb, ce in zip(bn["chapters"], en["chapters"]):
        a, b = cb.get("counts", {}), ce.get("counts", {})
        cells = []
        for k in ("objectives", "worked_examples", "ex_mcq", "ex_cq", "ex_sq"):
            x, y = a.get(k, 0), b.get(k, 0)
            conf = confirmed.get(f"ch{cb['number']:02d}", {}).get(k)
            if conf and conf.get("bn") == x and conf.get("en") == y:
                cells.append(f"{x}/{y} (book)")
                notes.append(f"- Ch {cb['number']} {k}: {conf['note']}")
                for c_ in (cb, ce):
                    c_["review"]["flags"] = [f for f in c_["review"]["flags"] if f != f"count-differs-from-other-version:{k}"]
                    flag = f"count-differs-in-printed-books:{k}"
                    if flag not in c_["review"]["flags"]:
                        c_["review"]["flags"].append(flag)
                continue
            cells.append(f"{x}/{y}" + ("" if x == y else " ⚠"))
            if x != y:
                for d_, c_ in ((bn, cb), (en, ce)):
                    flag = f"count-differs-from-other-version:{k}"
                    if flag not in c_["review"]["flags"]:
                        c_["review"]["flags"].append(flag)
        md.append(f"| {cb['number']} | " + " | ".join(cells) + " |")
    if notes:
        md += ["", "`(book)` = the two printed books really differ here; checked on the page images by the agent:", ""] + notes
    for d, p in ((bn, bn_path), (en, en_path)):
        Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "pairing-report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # manifest for the dataset version tag
    root = out.parent
    files = []
    for p in sorted(root.glob("*/*-[be][nn].json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        files.append(
            {
                "file": str(p.relative_to(root)),
                "book_id": d["book"]["id"],
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "counts": {k: len(d[k]) for k in ("chapters", "topics", "objectives", "worked_examples", "exercises")},
                "verified_items": sum(
                    1 for k in ("chapters", "topics", "objectives", "worked_examples", "exercises") for x in d[k] if x["review"]["verified"]
                ),
            }
        )
    manifest = {
        "dataset": "nctb-data",
        "dataset_version": bn["dataset_version"],
        "tag": f"nctb-data@{bn['dataset_version']}",
        "edition": bn["book"]["edition"],
        "id_scheme": "see IDS.md",
        "status": "draft: machine-extracted, agent spot-checked, not human-verified",
        "content_policy": "Structure, IDs, chapter/section titles, learning objectives and page pointers only. No body text, no exercise or worked-example text. NCTB reserves all rights in the textbooks.",
        "books": files,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"paired {checked} sections; {len(rows)} rows need review")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
