"""Apply a filled-in review CSV back to the data: the only way an item becomes verified=true.

verdict ok   -> verified=true, verified_by=reviewer, verified_at=today
verdict fix  -> value replaced by corrected_value, then verified=true
verdict drop -> item removed (IDs are never reused)

Usage: python3 pipeline/apply_review.py <review.csv> <data-subject-dir>
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

LISTS = ("chapters", "topics", "objectives", "worked_examples", "exercises")


def main(csv_path: str, data_dir: str) -> None:
    rows = [r for r in csv.DictReader(open(csv_path, encoding="utf-8")) if r.get("verdict", "").strip()]
    files = {p: json.loads(p.read_text(encoding="utf-8")) for p in Path(data_dir).glob("*-[be]n.json")}
    done = 0
    for r in rows:
        verdict, reviewer = r["verdict"].strip().lower(), r.get("reviewer", "").strip()
        if not reviewer:
            raise SystemExit(f"{r['id']}: reviewer name is required")
        for d in files.values():
            for key in LISTS:
                for item in list(d[key]):
                    if item["id"] != r["id"]:
                        continue
                    if verdict == "drop":
                        d[key].remove(item)
                    else:
                        if verdict == "fix" and r["field"] in ("title", "text") and r["corrected_value"].strip():
                            item[r["field"]] = r["corrected_value"].strip()
                        item["review"].update(verified=True, verified_by=reviewer, verified_at=date.today().isoformat(), flags=[])
                    done += 1
    for p, d in files.items():
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"applied {done} review rows")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
