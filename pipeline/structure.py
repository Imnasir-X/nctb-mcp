"""Step 3 of the pipeline: turn per-page OCR text into the nctb-data JSON for one book.

Usage:
  python3 pipeline/structure.py <book-config.json> <ocr-dir> <out.json>

Inputs
- book config (pipeline/books/*.json): book metadata and the chapter list transcribed by hand
  from the printed contents page (never from OCR).
- ocr dir: p001.txt ... one Tesseract text file per PDF page.
- pipeline/books/<book>.corrections.json (optional): per-ID title fixes made after looking at the
  page image; applied last and marked agent_checked.

What is stored: IDs, numbers, titles of chapters and sections, learning-objective sentences and
page pointers. What is NOT stored: body text, worked-example text, exercise text.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fix_bangla import bn_to_int, fix_line  # noqa: E402

D = r"[০-৯0-9]"

LANG = {
    "bn": {
        "objectives_start": re.compile(r"(অধ্যায়|পাঠ)\s*শেষে\s*আমরা"),
        "exercise_start": re.compile(r"নমুনা\s*প্রশ্ন|^\W{0,4}\s*অনুশীলনী"),
        "kinds": [
            ("mcq", re.compile(r"বহুনির্বাচনি")),
            ("cq", re.compile(r"সৃজনশীল\s*প্রশ্ন")),
            ("sq", re.compile(r"সংক্ষিপ্ত\s*(উত্তর)?\s*প্রশ্ন|অতি\s*সংক্ষিপ্ত")),
            ("num", re.compile(r"গাণিতিক\s*(সমস্যা|প্রশ্ন)")),
        ],
        # "উদাহরণ: <question>" is used once (p.150) where the en book prints "Question:"
        "worked_q": re.compile(r"^\W{0,3}\s*(প্রশ্ন\s*[:ঃ：]|উদাহরণ\s*[:ঃ：]\s*\S)"),
        # the MCQ instruction line; on p.300 (ch 10) it stands in for the missing MCQ heading
        "mcq_hint": re.compile(r"সঠিক\s*উত্তর\S*\s*পাশে\s*টিক"),
        "cq_parts": ["ক", "খ", "গ", "ঘ"],
        "part_re": re.compile(r"^\W{0,2}\(?\s*(ক|খ|গ|ঘ)\s*\)"),
    },
    "en": {
        "objectives_start": re.compile(r"(end of this chapter|After (studying|reading) this chapter).*(able|will)", re.I),
        "exercise_start": re.compile(r"Sample\s*Questions|^\W{0,4}\s*Exercises?\s*$", re.I),
        "kinds": [
            ("mcq", re.compile(r"Multiple\s*choice", re.I)),
            ("cq", re.compile(r"Creative\s*questions?", re.I)),
            ("sq", re.compile(r"Short\s*(Answer\s*)?Questions?", re.I)),
            ("num", re.compile(r"(Mathematical|Numerical)\s*(problems?|questions?)", re.I)),
        ],
        # Case-sensitive on purpose: "...a crucial question: how do we..." is body text, not a worked
        # example. Allows OCR variants seen in the scans ("Queston:", "Question :").
        # "Example: <question>" (pp.137, 308) is a worked example; a bare "Example:" box title is not.
        "worked_q": re.compile(r"^\W{0,3}\s*([QO0][uo]?e?st?i?on\s*[:：;]|Example\s*[:;：]\s*\S)"),
        "mcq_hint": re.compile(r"(Put|Give)\s+(a\s+)?tick", re.I),
        "cq_parts": ["a", "b", "c", "d"],
        "part_re": re.compile(r"^\W{0,2}\(?\s*([abcd])\s*\)"),
    },
}

HEADING = re.compile(
    rf"^\W{{0,2}}\s*({D}{{1,2}})\s*[.।]\s*({D}{{1,2}})(?:\s*[.।]\s*({D}{{1,2}}))?\s*[.:।]?\s+(\S.*)$"
)
ITEM = re.compile(r"^\W{0,2}\s*([০-৯0-9©]{1,2})\s*[.।]\s*(\S.*)?$")
# second/third part of a worked example printed with its own label: "(b)", "(খ)", OCR "(8)" for খ
CONTINUATION_PART = re.compile(r"^\s*\(\s*(b|c|d|খ|গ|ঘ|8)\s*\)")
BULLET = re.compile(r"^\s*(?:[*•»«®°o●▪◦\-–—¢e]|[0O@©]\))(?:\s*[—–-])?\s+(?P<text>.*)$")


NUM_GLUED = re.compile(r"^(\W{0,2}\s*[০-৯]{1,2}[.।][০-৯]{1,2}(?:[.।][০-৯]{1,2})?)(?=[\u0985-\u09B9])")
RUNNING_HEAD = re.compile(
    r"^\W{0,2}([০-৯0-9]{1,3}\s+(পদার্থবিজ্ঞান|Physics)\s*$)|ফর্মা\s*-|^\s*[০-৯0-9]{1,3}\s*$"
)


def is_running_head(line: str, titles: list[str]) -> bool:
    """Page headers/footers: '২ পদার্থবিজ্ঞান', '<chapter title> ৩', 'ফর্মা-১, ...', bare page numbers."""
    s = line.strip()
    if re.match(r"^\W{0,2}[০-৯0-9]{1,2}\s*[.।]\s*[০-৯0-9]", s):
        return False
    if RUNNING_HEAD.search(s):
        return True
    m = re.match(r"^\W{0,2}(.*?)\s*[©®]?\s*[০-৯0-9]{0,3}\s*$", s)
    if m and len(s) < 60:
        core = re.sub(r"[^\u0980-\u09ffA-Za-z]", "", m.group(1)).lower()
        for t in titles:
            tc = re.sub(r"[^\u0980-\u09ffA-Za-z]", "", t).lower()
            if core and tc and (core == tc or (len(core) > 6 and _similar(core, tc) > 0.8)):
                return True
    return False


def _similar(a: str, b: str) -> float:
    from difflib import SequenceMatcher

    return SequenceMatcher(None, a, b).ratio()


def pages(ocr_dir: Path, titles: list[str]) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for f in sorted(ocr_dir.glob("p[0-9][0-9][0-9].txt")):
        n = int(f.stem[1:])
        lines = f.read_text(encoding="utf-8").splitlines()
        # "৫.৩.৩প্যাসকেলের সূত্র": OCR drops the space between a Bangla section number and its title
        lines = [NUM_GLUED.sub(r"\1 ", ln) for ln in lines]
        out[n] = [ln for ln in lines if not is_running_head(ln, titles)]
    return out


# OCR reads some Bangla digits as Latin look-alikes.
DIGIT_CONFUSIONS = {"8": "৪", "©": "৩"}


def item_number(raw: str, expected: int, lang: str) -> int | None:
    num = bn_to_int(raw)
    if num == expected or lang != "bn":
        return num
    alt = "".join(DIGIT_CONFUSIONS.get(ch, ch) for ch in raw)
    alt_num = bn_to_int(alt)
    return alt_num if alt_num == expected else num


def split_alt(title: str) -> tuple[str, str | None]:
    """'পদার্থবিজ্ঞান (Physics)' -> ('পদার্থবিজ্ঞান', 'Physics'). Only Latin parentheticals."""
    m = re.match(r"^(.*?)\s*\(([A-Za-z][^()]*)\)\s*[:.]?\s*$", title)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return title.strip().rstrip(":").strip(), None


EN_VERBS = (
    "explain describe calculate determine measure analyse analyze realize realise find use demonstrate "
    "identify compare apply solve show state evaluate interpret verify distinguish define understand "
    "draw construct investigate perform recognize recognise create assess estimate express mention "
    "make discuss classify differentiate design plot read appreciate be"
).split()


def split_objectives(lines: list[tuple[str, int]], v: str) -> list[tuple[str, int]]:
    """Turn the raw lines after 'By the end of this chapter...' into one string per outcome."""
    pieces: list[tuple[str, int]] = []
    for text, p in lines:
        t = text.strip()
        if v == "en":
            # OCR turns the bullet into a stray 'e'/'o' mid-line: '... signs. e measure ...'
            t = re.sub(r"(?<=[.;])\s+[eo»«•*©®]\s+(?=[a-z])", " \n", t)
            t = re.sub(r"^[eo»«•*©®¢°]\s*[—–-]?\s+(?=[a-z])", "", t)
        for part in t.split("\n"):
            part = re.sub(r"^[^A-Za-z\u0980-\u09ff\[(]+", "", part.strip())
            if v == "en" and re.fullmatch(r"[A-Za-z]{1,3}", part):
                # the vertical "2026" printed in the margin OCRs as a stray "ny"/"ey" line
                continue
            if part:
                pieces.append((part, p))
    sentences: list[tuple[str, int]] = []
    cur, cur_p = "", 0
    for t, p in pieces:
        first = re.sub(r"[^a-z]", "", t.split(" ")[0].lower()) if v == "en" else ""
        if cur and v == "en" and first in EN_VERBS:
            # a new outcome starts on this line even though OCR lost the full stop
            sentences.append((cur.strip(), cur_p))
            cur = ""
        if not cur:
            cur_p = p
        cur = (cur + " " + t).strip()
        while True:
            m = re.search(r"ব\s*[।.]" if v == "bn" else r"\.(?=\s|$)", cur)
            if not m:
                break
            sentences.append((cur[: m.end()].strip(), cur_p))
            cur = cur[m.end():].strip()
            cur_p = p
    if cur and (v == "en" or re.search(r"(পারব|হব|করব)$", cur)):
        sentences.append((cur, cur_p))
    out: list[tuple[str, int]] = []
    for t, p in sentences:
        if v == "bn":
            if not re.search(r"(পারব|হব|করব)\s*[।.]?$", t):
                break
            if not t.endswith("।"):
                t = t.rstrip(". ") + "।"
        else:
            # outcomes start with a lower-case verb ("explain ..."); body text starts with a capital
            # (one outcome on p.305 starts with a capital verb: "Make users aware ...")
            first = re.sub(r"[^a-z]", "", t.split(" ")[0].lower())
            if not (re.match(r"^[a-z]", t) or first in EN_VERBS):
                break
        out.append((t, p))
    return out


def review(flags: list[str] | None = None, agent_checked: bool = False) -> dict:
    return {
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "agent_checked": agent_checked,
        "flags": sorted(set(flags or [])),
    }


def match_en(en_topics: list[dict], chapter: int, alt: str | None) -> str | None:
    """Section number of the English-book heading in this chapter whose title matches `alt`."""
    if not alt:
        return None
    from difflib import SequenceMatcher

    a = " ".join(re.findall(r"[a-z]+", alt.lower()))
    best, best_r = None, 0.0
    for t in en_topics:
        if not t["number"].startswith(f"{chapter}."):
            continue
        b = " ".join(re.findall(r"[a-z]+", t["title"].lower()))
        r = 1.0 if a and a == b else SequenceMatcher(None, a, b).ratio()
        if r > best_r:
            best, best_r = t["number"], r
    return best if best_r >= 0.8 else None


def main(cfg_path: str, ocr_dir: str, out_path: str, en_path: str | None = None) -> None:
    cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
    en_topics: list[dict] = (
        json.loads(Path(en_path).read_text(encoding="utf-8"))["topics"] if en_path and Path(en_path).exists() else []
    )
    corr_path = Path(cfg_path).with_suffix("").as_posix() + ".corrections.json"
    corrections: dict = (
        json.loads(Path(corr_path).read_text(encoding="utf-8")) if Path(corr_path).exists() else {}
    )
    v = cfg["book"]["version"]
    L = LANG[v]
    pg = pages(Path(ocr_dir), [c["title"] for c in cfg["chapters"]] + cfg.get("running_heads", []))
    # OCR line fixes made after looking at the page image: {"<pdf page>": [[wrong, right], ...]}
    for pnum, fixes in corrections.get("_ocr_line_fixes", {}).items():
        lines = pg.get(int(pnum), [])
        for wrong, right in fixes:
            hit = [i for i, ln in enumerate(lines) if wrong in ln]
            if not hit:
                raise SystemExit(f"_ocr_line_fixes: {wrong!r} not found on PDF page {pnum}")
            for i in hit:
                lines[i] = lines[i].replace(wrong, right)
    off = cfg["book"]["page_offset"]
    base = cfg["book"]["id"]
    last_pdf = cfg["last_body_pdf_page"]

    def pref(pdf: int) -> dict:
        printed = pdf - off
        return {"printed": printed if printed >= 1 else None, "pdf": pdf}

    chapters, topics, objectives, examples, exercises = [], [], [], [], []
    fixes_log: list[dict] = []
    toc = cfg["chapters"]
    for i, ch in enumerate(toc):
        n = ch["number"]
        cid = f"{base}:ch{n:02d}"
        ckey = cid.replace(f":{v}:", ":")
        start = ch["printed_start"] + off
        end = (toc[i + 1]["printed_start"] + off - 1) if i + 1 < len(toc) else last_pdf
        flags: list[str] = []

        # ---- walk pages
        in_ex = False
        kind: str | None = None
        last_item: dict[str, int] = {}
        current_topic: str | None = None
        seen_numbers: set[str] = set()
        last_t = 0
        last_s: dict[int, int] = {}
        unresolved: list[str] = []
        obj_mode = False
        obj_lines: list[tuple[str, int]] = []
        obj_start_page = start
        we_n = 0
        last_cq: dict | None = None

        for p in range(start, end + 1):
            lines = pg.get(p)
            if lines is None:
                flags.append(f"missing-ocr-page-{p}")
                continue
            for raw in lines:
                line = raw.strip()
                if not line:
                    continue
                # objectives block (first pages of the chapter only)
                if not in_ex and p <= start + 3 and not obj_lines and L["objectives_start"].search(line):
                    obj_mode = True
                    obj_start_page = p
                    continue
                if obj_mode:
                    hm = HEADING.match(line)
                    if (hm and bn_to_int(hm.group(1)) == n) or L["exercise_start"].search(line) or p > obj_start_page + 1:
                        obj_mode = False
                    else:
                        b = BULLET.match(line)
                        obj_lines.append((b.group("text") if b else line, p))
                        continue

                if not in_ex and L["exercise_start"].search(line):
                    in_ex = True
                    continue
                if not in_ex and L["kinds"][0][1].search(line) and len(line) < 60:
                    # the "Sample questions" heading OCR'd as noise (ch 13 bn, p.364): the MCQ
                    # heading also opens the exercise section
                    in_ex = True
                    kind = "mcq"
                    continue

                if in_ex:
                    for k, rx in L["kinds"]:
                        if rx.search(line) and len(line) < 60:
                            kind = k
                            break
                    else:
                        if kind is None and L["mcq_hint"].search(line):
                            kind = "mcq"
                            continue
                        if kind is None:
                            continue
                        im = ITEM.match(line)
                        if im:
                            exp = last_item.get(kind, 0) + 1
                            num = item_number(im.group(1), exp, v)
                            if num is not None and num == exp + 1 and exp > 1:
                                flags.append(f"exercise-number-gap:{kind}{exp:02d}")
                            if num is not None and exp <= num <= exp + 1:
                                last_item[kind] = num
                                item = {
                                    "id": f"{cid}:ex:{kind}{num:02d}",
                                    "chapter_id": cid,
                                    "kind": kind,
                                    "number": num,
                                    "page": pref(p),
                                    "review": review(),
                                }
                                if kind == "cq":
                                    item["parts"] = []
                                    last_cq = item
                                exercises.append(item)
                                continue
                        if kind == "cq" and last_cq is not None:
                            pm = L["part_re"].match(line)
                            if pm and pm.group(1) not in last_cq["parts"]:
                                last_cq["parts"].append(pm.group(1))
                    continue

                # body: section headings
                hm = HEADING.match(line)
                if hm:
                    raw_nums = [x for x in hm.group(1, 2, 3) if x]
                    if v == "bn":
                        # section numbers are printed in Bangla digits; an ASCII 8 is OCR for ৪
                        a, b2, c = (bn_to_int("".join(DIGIT_CONFUSIONS.get(ch, ch) for ch in x)) if x else None for x in hm.group(1, 2, 3))
                    else:
                        a, b2, c = (bn_to_int(x) if x else None for x in hm.group(1, 2, 3))
                    ascii_digits = v == "bn" and any(re.search(r"[0-9]", x) for x in raw_nums[1:])
                    second_raw = hm.group(2)
                    resolved_by = None
                    if ascii_digits and a == n:
                        # Latin digits inside a Bangla section number are OCR noise (৪->8, ৩->9 ...).
                        # Recover the number from the English book: same chapter, same English term.
                        _, alt_guess = split_alt(fix_line(hm.group(4))[0])
                        cand = match_en(en_topics, n, alt_guess)
                        if cand:
                            parts = [int(x) for x in cand.split(".")]
                            b2, c = parts[1], (parts[2] if len(parts) > 2 else None)
                            second_raw = "x"
                            resolved_by = "en-pairing"
                        elif b2 is not None and not second_raw.startswith(("০", "0")) and (
                            (c is None and b2 == last_t + 1)
                            or (c is not None and b2 == last_t and c == last_s.get(b2, 0) + 1)
                            or (c == 1 and b2 == last_t + 1)
                        ):
                            resolved_by = "sequence"
                        else:
                            if len(hm.group(4)) < 60 and not hm.group(4).rstrip().endswith(("।", ".")):
                                unresolved.append(hm.group(0)[:80])
                            continue
                    plausible = resolved_by is not None or b2 is not None and b2 <= last_t + 2 and (c is None or (b2 <= last_t and c <= last_s.get(b2, 0) + 2) or (b2 == last_t + 1 and c <= 2))
                    if a == n and b2 and not second_raw.startswith(("০", "0")) and plausible:
                        number = f"{a}.{b2}" + (f".{c}" if c else "")
                        if number not in seen_numbers:
                            last_t = max(last_t, b2)
                            if c:
                                last_s[b2] = max(last_s.get(b2, 0), c)
                            seen_numbers.add(number)
                            title_raw = hm.group(4)
                            title_fixed, applied = fix_line(title_raw)
                            title, alt = split_alt(title_fixed) if v == "bn" else (title_fixed.rstrip(":").strip(), None)
                            tid = f"{cid}:t{b2:02d}" + (f":s{c:02d}" if c else "")
                            tflags = {"en-pairing": ["number-from-en-pairing"], "sequence": ["ocr-digit-confusion"]}.get(resolved_by or "", [])
                            if re.search(r"[A-Z]{2,}|[@#$%^&*~{}<>\\|]|\b[A-Z]\b|\d@", title):
                                tflags.append("ocr-uncertain")
                            if v == "bn" and re.search(r"[A-Za-z]", title):
                                tflags.append("ocr-uncertain")
                            if applied:
                                fixes_log.append({"id": tid, "fixes": applied})
                            topics.append(
                                {
                                    "id": tid,
                                    "concept_key": tid.replace(f":{v}:", ":"),
                                    "concept_key_checked": False,
                                    "chapter_id": cid,
                                    "parent_id": f"{cid}:t{b2:02d}" if c else None,
                                    "number": number,
                                    "level": "subtopic" if c else "topic",
                                    "title": title,
                                    "title_alt": alt,
                                    "page": pref(p),
                                    "review": review(tflags),
                                    "_raw": title_raw,
                                }
                            )
                            current_topic = f"{cid}:t{b2:02d}"
                            continue
                wq = L["worked_q"].match(line)
                if wq and CONTINUATION_PART.match(line[wq.end():]):
                    # "প্রশ্ন: (b) ..." continues the previous worked example (seen on p.93 of the bn book)
                    continue
                if wq:
                    we_n += 1
                    examples.append(
                        {
                            "id": f"{cid}:we{we_n:02d}",
                            "chapter_id": cid,
                            "topic_id": current_topic,
                            "number": we_n,
                            "page": pref(p),
                            "review": review(),
                        }
                    )

        # objectives: join the block, split into sentences, keep the leading run of outcomes
        obj_buf = split_objectives(obj_lines, v)
        for k, (t, pp) in enumerate(obj_buf, start=1):
            fixed, applied = fix_line(t)
            oid = f"{cid}:o{k:02d}"
            of = []
            if re.search(r"\b[A-Z]{2,}\b|[@#$%^&*~{}<>\\]", fixed) and v == "bn":
                of.append("ocr-uncertain")
            if applied:
                fixes_log.append({"id": oid, "fixes": applied})
            objectives.append(
                {"id": oid, "chapter_id": cid, "number": k, "text": fixed, "page": pref(pp), "review": review(of)}
            )
        if not obj_buf:
            flags.append("objectives-not-found")

        for u in unresolved:
            flags.append("heading-number-unreadable:" + u)

        # gap check on section numbers
        tops = sorted({int(t["number"].split(".")[1]) for t in topics if t["chapter_id"] == cid})
        if tops:
            missing = [x for x in range(1, max(tops) + 1) if x not in tops]
            if missing:
                flags.append("topic-number-gap:" + ",".join(str(m) for m in missing))
        if not in_ex:
            flags.append("exercise-section-not-found")

        counts = {
            "topics": sum(1 for t in topics if t["chapter_id"] == cid and t["level"] == "topic"),
            "subtopics": sum(1 for t in topics if t["chapter_id"] == cid and t["level"] == "subtopic"),
            "objectives": sum(1 for o in objectives if o["chapter_id"] == cid),
            "worked_examples": sum(1 for e in examples if e["chapter_id"] == cid),
        }
        for k, _ in L["kinds"]:
            counts[f"ex_{k}"] = sum(1 for e in exercises if e["chapter_id"] == cid and e["kind"] == k)

        chapters.append(
            {
                "id": cid,
                "concept_key": ckey,
                "number": n,
                "title": ch["title"],
                "title_alt": ch.get("title_alt"),
                "pages": {"start": pref(start), "end": pref(end)},
                "counts": counts,
                "review": review(flags, agent_checked=True),
            }
        )

    # hand corrections (made after viewing the page image)
    for item in topics + objectives + examples + exercises + chapters:
        c = corrections.get(item["id"])
        if not c:
            continue
        for key in ("title", "title_alt", "text"):
            if key in c:
                item[key] = c[key]
        if "page_pdf" in c:
            item["page"] = pref(c["page_pdf"])
        item["review"]["agent_checked"] = True
        item["review"]["flags"] = [f for f in item["review"]["flags"] if f != "ocr-uncertain"]
        for pre in c.get("clear_flags", []):
            # e.g. a "heading-number-unreadable" flag whose heading was then added by hand
            item["review"]["flags"] = [f for f in item["review"]["flags"] if not f.startswith(pre)]
    # topics added by hand (missed by OCR)
    for tid, c in corrections.items():
        if tid.startswith("_"):
            continue
        if c.get("add") and not any(t["id"] == tid for t in topics):
            cid = tid.rsplit(":", 1)[0] if ":s" not in tid else tid.rsplit(":", 2)[0]
            parts = tid.split(":")
            chn = int(parts[4][2:])
            tn = int(parts[5][1:])
            sn = int(parts[6][1:]) if len(parts) > 6 else None
            topics.append(
                {
                    "id": tid,
                    "concept_key": tid.replace(f":{v}:", ":"),
                    "concept_key_checked": False,
                    "chapter_id": cid,
                    "parent_id": f"{cid}:t{tn:02d}" if sn else None,
                    "number": f"{chn}.{tn}" + (f".{sn}" if sn else ""),
                    "level": "subtopic" if sn else "topic",
                    "title": c["title"],
                    "title_alt": c.get("title_alt"),
                    "page": pref(c["page_pdf"]),
                    "review": review(["added-by-hand"], agent_checked=True),
                    "_raw": "",
                }
            )
    # drop items marked as false positives after looking at the page image (IDs are not reused)
    topics = [t for t in topics if not corrections.get(t["id"], {}).get("drop")]
    objectives = [o for o in objectives if not corrections.get(o["id"], {}).get("drop")]
    examples = [e for e in examples if not corrections.get(e["id"], {}).get("drop")]
    exercises = [x for x in exercises if not corrections.get(x["id"], {}).get("drop")]

    def sort_key(t: dict) -> tuple:
        return tuple(int(x) for x in t["number"].split("."))

    topics.sort(key=sort_key)
    raw = {t["id"]: t.pop("_raw") for t in topics}

    # recompute chapter gap flags after corrections
    for ch in chapters:
        nums = sorted({int(t["number"].split(".")[1]) for t in topics if t["chapter_id"] == ch["id"]})
        ch["review"]["flags"] = [f for f in ch["review"]["flags"] if not f.startswith("topic-number-gap")]
        if nums:
            missing = [x for x in range(1, max(nums) + 1) if x not in nums]
            if missing:
                ch["review"]["flags"].append("topic-number-gap:" + ",".join(map(str, missing)))
        subs: dict[int, set[int]] = {}
        for t in topics:
            if t["chapter_id"] == ch["id"] and t["level"] == "subtopic":
                _, tb, tc = (int(x) for x in t["number"].split("."))
                subs.setdefault(tb, set()).add(tc)
        skips = set(corrections.get("_book_skips", {}).get(ch["id"], []))
        for sk in sorted(skips):
            ch["review"]["flags"].append(f"book-skips-number:{sk}")
        for tb, cs in sorted(subs.items()):
            gap = [x for x in range(1, max(cs) + 1) if x not in cs and f"{ch['number']}.{tb}.{x}" not in skips]
            if gap:
                ch["review"]["flags"].append(
                    "subtopic-number-gap:" + ",".join(f"{ch['number']}.{tb}.{x}" for x in gap)
                )
        ch["counts"]["topics"] = sum(1 for t in topics if t["chapter_id"] == ch["id"] and t["level"] == "topic")
        ch["counts"]["subtopics"] = sum(1 for t in topics if t["chapter_id"] == ch["id"] and t["level"] == "subtopic")
        ch["counts"]["objectives"] = sum(1 for o in objectives if o["chapter_id"] == ch["id"])
        ch["counts"]["worked_examples"] = sum(1 for e in examples if e["chapter_id"] == ch["id"])
        for k, _ in L["kinds"]:
            ch["counts"][f"ex_{k}"] = sum(1 for e in exercises if e["chapter_id"] == ch["id"] and e["kind"] == k)
        if ch["counts"]["objectives"] and "objectives-not-found" in ch["review"]["flags"]:
            ch["review"]["flags"].remove("objectives-not-found")

    out = {
        "dataset": "nctb-data",
        "dataset_version": cfg["dataset_version"],
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "book": cfg["book"],
        "chapters": chapters,
        "topics": topics,
        "objectives": objectives,
        "worked_examples": examples,
        "exercises": exercises,
    }
    Path(out_path).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    side = Path(out_path).with_suffix(".pipeline-log.json")
    side.write_text(
        json.dumps({"ocr_word_fixes": fixes_log, "raw_heading_ocr": raw}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(
        f"{base}: {len(chapters)} chapters, {len(topics)} topics, {len(objectives)} objectives, "
        f"{len(examples)} worked examples, {len(exercises)} exercise items"
    )


if __name__ == "__main__":
    main(*sys.argv[1:5])
