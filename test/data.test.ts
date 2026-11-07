import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { join } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import { Catalog, normalizeClass } from "../src/data.js";
import { normalize, toAsciiDigits, toBanglaDigits, tokens } from "../src/text.js";

const dataDir = join(__dirname, "..", "data");
const catalog = Catalog.load(dataDir);
const schema = JSON.parse(readFileSync(join(dataDir, "schema", "nctb-data.schema.json"), "utf8"));
const ID =
  /^nctb:[a-z]+:c\d{1,2}(-\d{1,2})?:(bn|en)(:ch\d{2}(:(t\d{2}(:s\d{2})?|o\d{2}|we\d{2}|ex:(mcq|sq|cq|num)\d{2}))?)?$/;

describe("bundled data", () => {
  it("has both Physics 9-10 books", () => {
    expect(catalog.books.map((b) => b.book.id).sort()).toEqual([
      "nctb:phy:c9-10:bn",
      "nctb:phy:c9-10:en",
    ]);
  });

  it("validates against the JSON Schema", () => {
    const ajv = new Ajv2020({ allErrors: true, strict: false });
    const validate = ajv.compile(schema);
    for (const b of catalog.books) {
      const ok = validate(b);
      expect(validate.errors ?? []).toEqual([]);
      expect(ok).toBe(true);
    }
  });

  it("IDs are unique, well formed and scoped to their book", () => {
    const seen = new Set<string>();
    for (const b of catalog.books) {
      const items = [
        ...b.chapters,
        ...b.topics,
        ...b.objectives,
        ...b.worked_examples,
        ...b.exercises,
      ];
      for (const it of items) {
        expect(it.id).toMatch(ID);
        expect(it.id.startsWith(b.book.id + ":")).toBe(true);
        expect(seen.has(it.id)).toBe(false);
        seen.add(it.id);
      }
    }
  });

  it("nothing is marked human-verified in v0.1", () => {
    for (const b of catalog.books)
      for (const it of [
        ...b.chapters,
        ...b.topics,
        ...b.objectives,
        ...b.worked_examples,
        ...b.exercises,
      ])
        expect(it.review.verified).toBe(false);
  });

  it("pages are inside the PDF and inside their chapter", () => {
    for (const b of catalog.books) {
      for (const c of b.chapters) {
        expect(c.pages.start.pdf).toBeLessThanOrEqual(c.pages.end.pdf);
        expect(c.pages.end.pdf).toBeLessThanOrEqual(b.book.source.pdf_pages);
        const inside = [...b.topics, ...b.objectives, ...b.worked_examples, ...b.exercises].filter(
          (x) => x.chapter_id === c.id,
        );
        for (const x of inside) {
          expect(x.page.pdf).toBeGreaterThanOrEqual(c.pages.start.pdf);
          expect(x.page.pdf).toBeLessThanOrEqual(c.pages.end.pdf);
        }
      }
    }
  });

  it("chapter titles match the printed contents pages", () => {
    const bn = catalog.findBook("physics", "9-10", "bn")!;
    const en = catalog.findBook("physics", "9-10", "en")!;
    expect(bn.chapters.map((c) => c.title)).toEqual([
      "ভৌত রাশি এবং তাদের পরিমাপ",
      "গতি",
      "বল",
      "কাজ, ক্ষমতা ও শক্তি",
      "পদার্থের অবস্থা ও চাপ",
      "বস্তুর ওপর তাপের প্রভাব",
      "তরঙ্গ ও শব্দ",
      "আলোর প্রতিফলন",
      "আলোর প্রতিসরণ",
      "স্থির বিদ্যুৎ",
      "চল বিদ্যুৎ",
      "বিদ্যুতের চৌম্বক ক্রিয়া",
      "তেজস্ক্রিয়তা ও ইলেকট্রনিকস",
    ]);
    expect(en.chapters.map((c) => c.pages.start.printed)).toEqual([
      1, 31, 61, 98, 127, 160, 187, 211, 242, 270, 299, 330, 347,
    ]);
  });

  it("full coverage: every chapter of both books has topics, objectives, worked examples and exercises", () => {
    for (const b of catalog.books) {
      for (const c of b.chapters) {
        const of = <T extends { chapter_id: string }>(xs: T[]) =>
          xs.filter((x) => x.chapter_id === c.id);
        expect(of(b.topics).length, `${c.id} topics`).toBeGreaterThan(0);
        expect(of(b.objectives).length, `${c.id} objectives`).toBeGreaterThan(0);
        expect(of(b.worked_examples).length, `${c.id} worked examples`).toBeGreaterThan(0);
        for (const kind of ["mcq", "cq", "sq"])
          expect(
            of(b.exercises).filter((x) => x.kind === kind).length,
            `${c.id} ${kind}`,
          ).toBeGreaterThan(0);
      }
    }
  });

  it("bn and en counts agree per chapter, except differences confirmed in the printed books", () => {
    const bn = catalog.findBook("physics", "9-10", "bn")!;
    const en = catalog.findBook("physics", "9-10", "en")!;
    const count = (xs: { chapter_id: string }[], id: string) =>
      xs.filter((x) => x.chapter_id === id).length;
    expect(bn.topics.length).toBe(en.topics.length);
    for (let i = 0; i < bn.chapters.length; i++) {
      const cb = bn.chapters[i]!;
      const ce = en.chapters[i]!;
      expect(count(bn.worked_examples, cb.id), `ch${cb.number} worked`).toBe(
        count(en.worked_examples, ce.id),
      );
      expect(count(bn.exercises, cb.id), `ch${cb.number} exercises`).toBe(
        count(en.exercises, ce.id),
      );
      const ob = count(bn.objectives, cb.id);
      const oe = count(en.objectives, ce.id);
      if (ob !== oe) expect(cb.review.flags).toContain("count-differs-in-printed-books:objectives");
    }
  });

  it("manifest checksums match the bundled files", () => {
    const manifest = JSON.parse(readFileSync(join(dataDir, "manifest.json"), "utf8"));
    for (const f of manifest.books) {
      const buf = readFileSync(join(dataDir, f.file.split("/").pop()));
      expect(createHash("sha256").update(buf).digest("hex"), f.file).toBe(f.sha256);
    }
  });

  it("no textbook body text: exercises and worked examples carry no text field", () => {
    for (const b of catalog.books) {
      for (const x of [...b.exercises, ...b.worked_examples]) expect("text" in x).toBe(false);
    }
  });
});

describe("text helpers", () => {
  it("digits both ways", () => {
    expect(toAsciiDigits("৩.২")).toBe("3.2");
    expect(toBanglaDigits("2026")).toBe("২০২৬");
  });
  it("normalize folds nukta forms, zero-width chars and case", () => {
    expect(normalize("\u09DF")).toBe(normalize("\u09AF\u09BC"));
    expect(normalize("Force\u200B (বল)")).toBe("force বল");
    expect(tokens("Newton's 3rd law, ৩.৮")).toEqual(["newton", "s", "3rd", "law", "3.8"]);
  });
  it("class aliases", () => {
    expect(normalizeClass("10")).toBe("9-10");
    expect(normalizeClass("নবম-দশম")).toBe("9-10");
    expect(normalizeClass("SSC")).toBe("9-10");
    expect(normalizeClass("11")).toBe("11");
    expect(normalizeClass(undefined)).toBeUndefined();
  });
  it("subject aliases", () => {
    for (const s of ["physics", "Physics", "পদার্থবিজ্ঞান", "পদার্থ বিজ্ঞান", "phy"])
      expect(catalog.subjectCode(s)).toBe("phy");
    expect(catalog.subjectCode("chemistry")).toBeUndefined();
  });
  it("counterparts", () => {
    expect(catalog.counterpart("nctb:phy:c9-10:bn:ch05")).toBe("nctb:phy:c9-10:en:ch05");
    expect(catalog.counterpart("nctb:none")).toBeUndefined();
    expect(catalog.counterpart("nctb:phy:c9-10:bn:ch01:o01")).toBeUndefined();
  });
});
