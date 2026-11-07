import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import {
  Catalog,
  type AnyItem,
  type BookData,
  type Chapter,
  type PageRef,
  type Review,
  type Topic,
} from "./data.js";

export { Catalog } from "./data.js";
export { normalize, toAsciiDigits, toBanglaDigits } from "./text.js";
export const VERSION = "0.1.0";

type ToolResult = { content: { type: "text"; text: string }[]; isError?: boolean };

const NOTICE =
  "Structure, IDs, objectives and page pointers only. Textbook content belongs to NCTB (all rights reserved); open the official PDF page for the text. Items are machine-extracted (OCR) and verified=false until a human checks them.";

function json(data: unknown): ToolResult {
  return { content: [{ type: "text", text: JSON.stringify(data, null, 1) }] };
}
function fail(message: string, hint?: unknown): ToolResult {
  return {
    content: [{ type: "text", text: JSON.stringify({ error: message, hint }, null, 1) }],
    isError: true,
  };
}

/** Source block attached to every item: where to read it in the official PDF. */
function source(book: BookData, page: PageRef) {
  return {
    book_id: book.book.id,
    printed_page: page.printed,
    pdf_page: page.pdf,
    pdf_urls: book.book.source.pdf_urls,
    official_listing_url: book.book.source.official_listing_url,
    edition: book.book.edition,
  };
}
function status(r: Review) {
  return { verified: r.verified, ...(r.flags.length ? { flags: r.flags } : {}) };
}

function chapterSummary(book: BookData, c: Chapter) {
  return {
    id: c.id,
    number: c.number,
    title: c.title,
    ...(c.title_alt ? { title_alt: c.title_alt } : {}),
    pages: {
      printed: [c.pages.start.printed, c.pages.end.printed],
      pdf: [c.pages.start.pdf, c.pages.end.pdf],
    },
    topics: book.topics.filter((t) => t.chapter_id === c.id && t.level === "topic").length,
    ...status(c.review),
  };
}
function topicSummary(book: BookData, t: Topic) {
  return {
    id: t.id,
    number: t.number,
    title: t.title,
    ...(t.title_alt ? { title_alt: t.title_alt } : {}),
    printed_page: t.page.printed,
    pdf_page: t.page.pdf,
    ...status(t.review),
  };
}

const versionSchema = z
  .enum(["bn", "en"])
  .optional()
  .describe(
    'Book version: "bn" = Bangla version (default), "en" = English version. Separate books with different page numbers.',
  );
const subjectSchema = z
  .string()
  .optional()
  .describe(
    'Subject in English, Bangla or romanised Bangla, e.g. "physics", "পদার্থবিজ্ঞান". Default physics (the only subject in v0.1).',
  );
const classSchema = z
  .string()
  .optional()
  .describe(
    'Class, e.g. "9", "10", "9-10" or "SSC". Classes 9 and 10 share one book. Default 9-10.',
  );

/** Resolve a chapter from an ID or from subject/class/version/number. */
function resolveChapter(
  cat: Catalog,
  args: { id?: string; subject?: string; class?: string; version?: "bn" | "en"; chapter?: number },
): { book: BookData; chapter: Chapter } | ToolResult {
  if (args.id) {
    const f = cat.get(args.id);
    if (!f)
      return fail(
        `Unknown ID ${args.id}`,
        "Use list_chapters or search_curriculum to get valid IDs.",
      );
    const chId =
      f.type === "chapter" ? f.item.id : "chapter_id" in f.item ? f.item.chapter_id : undefined;
    const ch = f.book.chapters.find((c) => c.id === chId);
    return ch ? { book: f.book, chapter: ch } : fail(`No chapter for ${args.id}`);
  }
  const book = cat.findBook(args.subject ?? "physics", args.class, args.version);
  if (!book) return fail("No book for that subject/class/version.", available(cat));
  if (args.chapter === undefined) return fail("Give an id or a chapter number.");
  const ch = book.chapters.find((c) => c.number === args.chapter);
  if (!ch)
    return fail(
      `Chapter ${args.chapter} not found; this book has chapters 1-${book.chapters.length}.`,
    );
  return { book, chapter: ch };
}

function available(cat: Catalog) {
  return cat.books.map((b) => ({
    book_id: b.book.id,
    subject: b.book.subject.name_en,
    subject_bn: b.book.subject.name_bn,
    class: b.book.class,
    version: b.book.version,
    edition: b.book.edition,
  }));
}

function describe(cat: Catalog, f: AnyItem) {
  const b = f.book;
  switch (f.type) {
    case "chapter": {
      const c = f.item;
      return {
        type: "chapter",
        ...chapterSummary(b, c),
        topics: b.topics.filter((t) => t.chapter_id === c.id).map((t) => topicSummary(b, t)),
        objective_ids: b.objectives.filter((o) => o.chapter_id === c.id).map((o) => o.id),
        counts: c.counts,
        counterpart_id: cat.counterpart(c.id),
        source: source(b, c.pages.start),
      };
    }
    case "topic": {
      const t = f.item;
      const ch = b.chapters.find((c) => c.id === t.chapter_id);
      const siblings = b.topics.filter((x) => x.chapter_id === t.chapter_id);
      const i = siblings.findIndex((x) => x.id === t.id);
      return {
        type: "topic",
        ...topicSummary(b, t),
        level: t.level,
        chapter: ch ? { id: ch.id, number: ch.number, title: ch.title } : undefined,
        parent_id: t.parent_id ?? null,
        subtopics: b.topics.filter((x) => x.parent_id === t.id).map((x) => topicSummary(b, x)),
        previous_id: siblings[i - 1]?.id ?? null,
        next_id: siblings[i + 1]?.id ?? null,
        worked_example_ids: b.worked_examples.filter((w) => w.topic_id === t.id).map((w) => w.id),
        counterpart_id: cat.counterpart(t.id),
        source: source(b, t.page),
      };
    }
    case "objective":
      return {
        type: "objective",
        id: f.item.id,
        number: f.item.number,
        text: f.item.text,
        chapter_id: f.item.chapter_id,
        ...status(f.item.review),
        source: source(b, f.item.page),
      };
    case "worked_example":
      return {
        type: "worked_example",
        id: f.item.id,
        number: f.item.number,
        chapter_id: f.item.chapter_id,
        topic_id: f.item.topic_id ?? null,
        ...status(f.item.review),
        source: source(b, f.item.page),
        note: "Pointer only; read the example on the PDF page.",
      };
    case "exercise":
      return {
        type: "exercise",
        id: f.item.id,
        kind: f.item.kind,
        number: f.item.number,
        parts: f.item.parts,
        chapter_id: f.item.chapter_id,
        ...status(f.item.review),
        source: source(b, f.item.page),
        note: "Pointer only; read the question on the PDF page.",
      };
  }
}

const KIND_LABEL = {
  mcq: "multiple choice (বহুনির্বাচনি)",
  cq: "creative question (সৃজনশীল), parts ক-ঘ / a-d",
  sq: "short answer (সংক্ষিপ্ত উত্তর)",
  num: "numerical problem (গাণিতিক সমস্যা)",
} as const;

/** Build the NCTB curriculum MCP server. */
export function createServer(catalog: Catalog = Catalog.load()): McpServer {
  const server = new McpServer({ name: "nctb-mcp", version: VERSION });
  const ro = { readOnlyHint: true, idempotentHint: true, openWorldHint: false } as const;

  server.registerTool(
    "list_chapters",
    {
      title: "List chapters of an NCTB textbook",
      description:
        "Start here. Lists the chapters of a Bangladesh NCTB textbook (v0.1: Class 9-10 / SSC Physics, 2026 edition, Bangla and English versions) with chapter IDs, titles, page ranges and topic counts. Use the returned IDs with get_topic, get_objectives and get_exercises.",
      inputSchema: { subject: subjectSchema, class: classSchema, version: versionSchema },
      annotations: ro,
    },
    async ({ subject, class: klass, version }) => {
      const book = catalog.findBook(subject ?? "physics", klass, version);
      if (!book)
        return fail("No book for that subject/class/version.", { available: available(catalog) });
      return json({
        book: {
          id: book.book.id,
          title: book.book.title,
          subject: book.book.subject.name_en,
          subject_bn: book.book.subject.name_bn,
          class: book.book.class,
          version: book.book.version,
          edition: book.book.edition,
          rights: book.book.rights_statement,
        },
        dataset_version: book.dataset_version,
        chapters: book.chapters.map((c) => chapterSummary(book, c)),
        source: {
          pdf_urls: book.book.source.pdf_urls,
          official_listing_url: book.book.source.official_listing_url,
          sha256: book.book.source.sha256,
        },
        other_books: available(catalog).filter((b) => b.book_id !== book.book.id),
        notice: NOTICE,
      });
    },
  );

  server.registerTool(
    "get_topic",
    {
      title: "Get a chapter, topic or item by ID",
      description:
        'Details for one curriculum item: a chapter (returns its numbered sections/topics), a topic such as "3.2" (returns subtopics, neighbours and its page), or an objective, worked-example or exercise ID. Pass an ID like nctb:phy:c9-10:bn:ch03 or nctb:phy:c9-10:bn:ch03:t02, or pass chapter (and optionally topic like "3.2") with subject/version. Every result has the official PDF page and a verified flag. Does not return textbook text.',
      inputSchema: {
        id: z.string().optional().describe("Any nctb: ID from another tool."),
        chapter: z.coerce
          .number()
          .int()
          .min(1)
          .optional()
          .describe("Chapter number, used when no id is given."),
        topic: z.coerce
          .string()
          .optional()
          .describe(
            'Section number as printed in the book, e.g. "3.2" or "1.3.4" (Bangla digits accepted).',
          ),
        subject: subjectSchema,
        class: classSchema,
        version: versionSchema,
      },
      annotations: ro,
    },
    async (args) => {
      if (args.id && !args.topic) {
        const f = catalog.get(args.id);
        if (!f)
          return fail(
            `Unknown ID ${args.id}`,
            "Use list_chapters or search_curriculum to get valid IDs.",
          );
        return json({ ...describe(catalog, f), notice: NOTICE });
      }
      const r = resolveChapter(catalog, args);
      if ("content" in r) return r;
      if (!args.topic)
        return json({
          ...describe(catalog, { type: "chapter", item: r.chapter, book: r.book }),
          notice: NOTICE,
        });
      const num = args.topic.replace(/[০-৯]/g, (d) => String("০১২৩৪৫৬৭৮৯".indexOf(d))).trim();
      const t = r.book.topics.find((x) => x.chapter_id === r.chapter.id && x.number === num);
      if (!t)
        return fail(`Topic ${num} not found in chapter ${r.chapter.number}.`, {
          topics: r.book.topics.filter((x) => x.chapter_id === r.chapter.id).map((x) => x.number),
        });
      return json({
        ...describe(catalog, { type: "topic", item: t, book: r.book }),
        notice: NOTICE,
      });
    },
  );

  server.registerTool(
    "search_curriculum",
    {
      title: "Search chapters, topics and objectives",
      description:
        'Find where a concept is taught, in Bangla or English (e.g. "ভরবেগ", "momentum", "Newton third law", "আলোর প্রতিসরণ"). Searches chapter titles, section headings and learning objectives. Returns small hits with IDs and pages; call get_topic on an ID for details. A Bangla query searches the Bangla-version book best, an English query the English-version book, unless version is set.',
      inputSchema: {
        query: z.string().min(1).describe("Words to find, Bangla or English."),
        version: versionSchema,
        subject: subjectSchema,
        limit: z.coerce.number().int().min(1).max(25).optional().describe("Max hits, default 8."),
      },
      annotations: ro,
    },
    async ({ query, version, subject, limit }) => {
      const hits = catalog.search(query, { version, subject, limit: limit ?? 8 });
      return json({
        query,
        hits: hits.map((h) => {
          const f = catalog.get(h.id) as AnyItem;
          const page = f.type === "chapter" ? f.item.pages.start : f.item.page;
          const title =
            f.type === "objective"
              ? f.item.text
              : f.type === "chapter" || f.type === "topic"
                ? f.item.title
                : f.item.id;
          const chapterId =
            f.type === "chapter" ? f.item.id : (f.item as { chapter_id: string }).chapter_id;
          return {
            id: h.id,
            type: h.type,
            ...(f.type === "topic" ? { number: f.item.number } : {}),
            title,
            chapter_id: chapterId,
            version: f.book.book.version,
            printed_page: page.printed,
            pdf_page: page.pdf,
            verified: f.item.review.verified,
          };
        }),
        ...(hits.length === 0
          ? { hint: "No match. Try the other language, a shorter word, or list_chapters." }
          : {}),
      });
    },
  );

  server.registerTool(
    "get_objectives",
    {
      title: "Learning objectives of a chapter",
      description:
        'The learning outcomes NCTB lists at the start of a chapter ("এই অধ্যায় শেষে আমরা ... পারব" / "By the end of this chapter we will be able to"). Pass a chapter ID (or any ID inside it), or chapter number with subject/version.',
      inputSchema: {
        id: z.string().optional().describe("Chapter ID or any ID inside the chapter."),
        chapter: z.coerce.number().int().min(1).optional(),
        subject: subjectSchema,
        class: classSchema,
        version: versionSchema,
      },
      annotations: ro,
    },
    async (args) => {
      const r = resolveChapter(catalog, args);
      if ("content" in r) return r;
      const objs = r.book.objectives.filter((o) => o.chapter_id === r.chapter.id);
      return json({
        chapter: { id: r.chapter.id, number: r.chapter.number, title: r.chapter.title },
        objectives: objs.map((o) => ({
          id: o.id,
          number: o.number,
          text: o.text,
          printed_page: o.page.printed,
          pdf_page: o.page.pdf,
          ...status(o.review),
        })),
        source: source(r.book, objs[0]?.page ?? r.chapter.pages.start),
        notice: NOTICE,
      });
    },
  );

  server.registerTool(
    "get_exercises",
    {
      title: "End-of-chapter exercises and worked examples (pointers)",
      description:
        "Lists the exercise items at the end of a chapter (multiple choice, creative/সৃজনশীল with parts ক-ঘ, short answer, numerical) and the worked examples inside it, as IDs with page numbers. Question text is NOT included (NCTB copyright): use the pdf_page to read it, or write your own practice questions for the topic.",
      inputSchema: {
        id: z.string().optional().describe("Chapter ID or any ID inside the chapter."),
        chapter: z.coerce.number().int().min(1).optional(),
        kind: z.enum(["mcq", "cq", "sq", "num"]).optional().describe("Only this kind."),
        subject: subjectSchema,
        class: classSchema,
        version: versionSchema,
      },
      annotations: ro,
    },
    async (args) => {
      const r = resolveChapter(catalog, args);
      if ("content" in r) return r;
      const ex = r.book.exercises.filter(
        (e) => e.chapter_id === r.chapter.id && (!args.kind || e.kind === args.kind),
      );
      const kinds = [...new Set(ex.map((e) => e.kind))];
      return json({
        chapter: { id: r.chapter.id, number: r.chapter.number, title: r.chapter.title },
        exercises: kinds.map((k) => ({
          kind: k,
          label: KIND_LABEL[k],
          items: ex
            .filter((e) => e.kind === k)
            .map((e) => ({
              id: e.id,
              number: e.number,
              ...(e.parts?.length ? { parts: e.parts } : {}),
              printed_page: e.page.printed,
              pdf_page: e.page.pdf,
              ...status(e.review),
            })),
        })),
        worked_examples: args.kind
          ? undefined
          : r.book.worked_examples
              .filter((w) => w.chapter_id === r.chapter.id)
              .map((w) => ({
                id: w.id,
                number: w.number,
                topic_id: w.topic_id ?? null,
                printed_page: w.page.printed,
                pdf_page: w.page.pdf,
                ...status(w.review),
              })),
        source: { book_id: r.book.book.id, pdf_urls: r.book.book.source.pdf_urls },
        notice: NOTICE,
      });
    },
  );

  return server;
}
