import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { normalize, tokens } from "./text.js";

export interface PageRef {
  printed: number | null;
  pdf: number;
}
export interface Review {
  verified: boolean;
  verified_by: string | null;
  verified_at: string | null;
  agent_checked: boolean;
  flags: string[];
}
export interface Book {
  id: string;
  subject: { code: string; name_bn: string; name_en: string; aliases: string[] };
  class: string;
  level?: string;
  version: "bn" | "en";
  edition: number;
  title: string;
  publisher: string;
  rights_statement: string;
  edition_history?: string[];
  page_offset: number;
  source: {
    official_listing_url: string;
    pdf_urls: string[];
    filename?: string;
    sha256: string;
    bytes: number;
    pdf_pages: number;
    retrieved_at?: string;
    text_layer?: string;
  };
}
export interface Chapter {
  id: string;
  concept_key: string;
  number: number;
  title: string;
  title_alt?: string | null;
  pages: { start: PageRef; end: PageRef };
  counts?: Record<string, number>;
  review: Review;
}
export interface Topic {
  id: string;
  concept_key: string;
  concept_key_checked?: boolean;
  chapter_id: string;
  parent_id?: string | null;
  number: string;
  level: "topic" | "subtopic";
  title: string;
  title_alt?: string | null;
  page: PageRef;
  review: Review;
}
export interface Objective {
  id: string;
  chapter_id: string;
  number: number;
  text: string;
  page: PageRef;
  review: Review;
}
export interface WorkedExample {
  id: string;
  chapter_id: string;
  topic_id?: string | null;
  number: number;
  page: PageRef;
  review: Review;
}
export interface Exercise {
  id: string;
  chapter_id: string;
  kind: "mcq" | "sq" | "cq" | "num";
  number: number;
  parts?: string[];
  page: PageRef;
  review: Review;
}
export interface BookData {
  dataset: "nctb-data";
  dataset_version: string;
  generated_at?: string;
  book: Book;
  chapters: Chapter[];
  topics: Topic[];
  objectives: Objective[];
  worked_examples: WorkedExample[];
  exercises: Exercise[];
}

export type AnyItem =
  | { type: "chapter"; item: Chapter; book: BookData }
  | { type: "topic"; item: Topic; book: BookData }
  | { type: "objective"; item: Objective; book: BookData }
  | { type: "worked_example"; item: WorkedExample; book: BookData }
  | { type: "exercise"; item: Exercise; book: BookData };

export type ItemType = AnyItem["type"];

const here = dirname(fileURLToPath(import.meta.url));

/** The bundled data directory: ../data from src/ (dev) or dist/ (published). */
export function defaultDataDir(): string {
  return process.env.NCTB_MCP_DATA_DIR ?? join(here, "..", "data");
}

const STOP = new Set([
  "the",
  "of",
  "and",
  "in",
  "a",
  "an",
  "to",
  "for",
  "class",
  "chapter",
  "nctb",
  "book",
  "ssc",
  "give",
  "me",
  "ও",
  "এবং",
  "এর",
  "কী",
  "কি",
  "অধ্যায়",
  "শ্রেণি",
  "শ্রেণী",
  "বই",
]);

const CLASS_9_10 = new Set([
  "9",
  "10",
  "910",
  "ssc",
  "নবম",
  "দশম",
  "নবমদশম",
  "classnine",
  "classten",
]);

/** Map user class input to a book class key. 9, 10, "9-10", SSC, নবম and দশম all mean the 9-10 book. */
export function normalizeClass(klass: string | undefined): string | undefined {
  if (!klass) return undefined;
  const k = normalize(klass).replace(/\s+/g, "");
  return CLASS_9_10.has(k) ? "9-10" : k;
}

export class Catalog {
  readonly books: BookData[];
  private readonly byId = new Map<string, AnyItem>();

  constructor(books: BookData[]) {
    this.books = books;
    for (const b of books) {
      for (const c of b.chapters) this.byId.set(c.id, { type: "chapter", item: c, book: b });
      for (const t of b.topics) this.byId.set(t.id, { type: "topic", item: t, book: b });
      for (const o of b.objectives) this.byId.set(o.id, { type: "objective", item: o, book: b });
      for (const w of b.worked_examples)
        this.byId.set(w.id, { type: "worked_example", item: w, book: b });
      for (const e of b.exercises) this.byId.set(e.id, { type: "exercise", item: e, book: b });
    }
  }

  /** Load every `<name>-bn.json` / `<name>-en.json` book file in a directory. */
  static load(dir = defaultDataDir()): Catalog {
    const files = readdirSync(dir).filter((f) => /^[a-z0-9-]+-(bn|en)\.json$/.test(f));
    const books = files
      .sort()
      .map((f) => JSON.parse(readFileSync(join(dir, f), "utf8")) as BookData)
      .filter((b) => b.dataset === "nctb-data");
    return new Catalog(books);
  }

  get(id: string): AnyItem | undefined {
    return this.byId.get(id.trim());
  }

  /** Resolve subject words (English, Bangla, romanised) to a subject code. */
  subjectCode(input: string): string | undefined {
    const n = normalize(input).replace(/\s+/g, "");
    for (const b of this.books) {
      const s = b.book.subject;
      const names = [s.code, s.name_en, s.name_bn, ...s.aliases];
      if (names.some((a) => normalize(a).replace(/\s+/g, "") === n)) return s.code;
    }
    return undefined;
  }

  /** Find a book by subject, class and version (default Bangla version). */
  findBook(subject: string, klass?: string, version?: string): BookData | undefined {
    const code = this.subjectCode(subject);
    if (!code) return undefined;
    const cls = normalizeClass(klass);
    const v = version === "en" ? "en" : "bn";
    return this.books.find(
      (b) =>
        b.book.subject.code === code &&
        b.book.version === v &&
        (cls === undefined || b.book.class === cls),
    );
  }

  /**
   * The same item in the other-language book. Chapters always pair up; topics pair up only
   * when both sides are marked concept_key_checked.
   */
  counterpart(id: string): string | undefined {
    const found = this.get(id);
    if (!found) return undefined;
    const v = found.book.book.version;
    const otherId = id.replace(`:${v}:`, `:${v === "bn" ? "en" : "bn"}:`);
    const o = this.get(otherId);
    if (!o || o.type !== found.type) return undefined;
    if (found.type === "topic") {
      const ok = found.item.concept_key_checked && (o.item as Topic).concept_key_checked;
      return ok ? otherId : undefined;
    }
    return found.type === "chapter" ? otherId : undefined;
  }

  /** Token search over chapter titles, topic headings and objectives. */
  search(
    query: string,
    opts: { version?: "bn" | "en"; subject?: string; limit?: number } = {},
  ): { id: string; type: ItemType; score: number }[] {
    const q = tokens(query).filter((t) => !STOP.has(t));
    if (q.length === 0) return [];
    const code = opts.subject ? this.subjectCode(opts.subject) : undefined;
    const subjectWords = new Set<string>();
    for (const b of this.books) {
      const s = b.book.subject;
      for (const a of [s.name_en, s.name_bn, s.code, ...s.aliases])
        for (const t of tokens(a)) subjectWords.add(t);
    }
    const content = q.filter((t) => !subjectWords.has(t));
    const terms = content.length > 0 ? content : q;
    const phrase = terms.join(" ");

    const hits: { id: string; type: ItemType; score: number }[] = [];
    for (const [id, entry] of this.byId) {
      if (entry.type === "worked_example" || entry.type === "exercise") continue;
      if (opts.version && entry.book.book.version !== opts.version) continue;
      if (code && entry.book.book.subject.code !== code) continue;
      const fields =
        entry.type === "objective"
          ? [entry.item.text]
          : [entry.item.title, entry.item.title_alt ?? "", String(entry.item.number)];
      const hay = normalize(fields.join(" "));
      const hayTokens = new Set(hay.split(" "));
      let score = 0;
      for (const t of terms) {
        if (hayTokens.has(t)) score += 3;
        else if (t.length >= 3 && hay.includes(t)) score += 2;
      }
      if (score === 0) continue;
      if (terms.length > 1 && hay.includes(phrase)) score += 4;
      if (entry.type === "chapter") score += 1.5;
      else if (entry.type === "topic") score += 1;
      hits.push({ id, type: entry.type, score });
    }
    hits.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
    return hits.slice(0, opts.limit ?? 10);
  }
}
