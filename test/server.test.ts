import { describe, expect, it, beforeAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer, Catalog } from "../src/index.js";

let client: Client;
const catalog = Catalog.load();

beforeAll(async () => {
  const [clientT, serverT] = InMemoryTransport.createLinkedPair();
  await createServer(catalog).connect(serverT);
  client = new Client({ name: "test", version: "0.0.0" });
  await client.connect(clientT);
});

async function call(
  name: string,
  args: Record<string, unknown>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): Promise<{ data: any; isError: boolean }> {
  const res = (await client.callTool({ name, arguments: args })) as {
    content: { type: string; text: string }[];
    isError?: boolean;
  };
  return { data: JSON.parse(res.content[0]?.text ?? "null"), isError: res.isError ?? false };
}

describe("tools", () => {
  it("exposes the five tools, read-only, with real descriptions", async () => {
    const { tools } = await client.listTools();
    expect(tools.map((t) => t.name).sort()).toEqual([
      "get_exercises",
      "get_objectives",
      "get_topic",
      "list_chapters",
      "search_curriculum",
    ]);
    for (const t of tools) {
      expect(t.description?.length).toBeGreaterThan(80);
      expect(t.annotations?.readOnlyHint).toBe(true);
    }
  });

  it("list_chapters: Bangla physics by Bangla subject name and class 9", async () => {
    const { data, isError } = await call("list_chapters", { subject: "পদার্থবিজ্ঞান", class: "9" });
    expect(isError).toBe(false);
    expect(data.book.id).toBe("nctb:phy:c9-10:bn");
    expect(data.chapters).toHaveLength(13);
    expect(data.chapters[2]).toMatchObject({
      id: "nctb:phy:c9-10:bn:ch03",
      number: 3,
      title: "বল",
    });
    expect(data.chapters[2].verified).toBe(false);
    expect(data.notice).toMatch(/NCTB/);
  });

  it("list_chapters: English version, romanised subject alias", async () => {
    const { data } = await call("list_chapters", {
      subject: "podartho biggan",
      version: "en",
      class: "SSC",
    });
    expect(data.book.id).toBe("nctb:phy:c9-10:en");
    expect(data.chapters[2].title).toBe("Force");
    expect(data.chapters[12].title).toBe("Radioactivity and Electronics");
  });

  it("list_chapters: unknown subject is an error listing what exists", async () => {
    const { data, isError } = await call("list_chapters", { subject: "astrology" });
    expect(isError).toBe(true);
    expect(data.hint.available.length).toBeGreaterThanOrEqual(2);
  });

  it("get_topic: chapter by number returns topics with pages and verified flags", async () => {
    const { data } = await call("get_topic", { chapter: 3 });
    expect(data.type).toBe("chapter");
    expect(data.id).toBe("nctb:phy:c9-10:bn:ch03");
    expect(data.topics.length).toBeGreaterThan(3);
    for (const t of data.topics) {
      expect(t.id.startsWith("nctb:phy:c9-10:bn:ch03:t")).toBe(true);
      expect(typeof t.pdf_page).toBe("number");
      expect(t.verified).toBe(false);
    }
    expect(data.source.pdf_page).toBe(data.pages.pdf[0]);
    expect(data.counterpart_id).toBe("nctb:phy:c9-10:en:ch03");
  });

  it("get_topic: by section number with Bangla digits, and by ID", async () => {
    const a = await call("get_topic", { chapter: 1, topic: "১.১" });
    expect(a.data.id).toBe("nctb:phy:c9-10:bn:ch01:t01");
    expect(a.data.source.pdf_page).toBeGreaterThan(5);
    const b = await call("get_topic", { id: a.data.id });
    expect(b.data.title).toBe(a.data.title);
    expect(b.data.next_id).toBeTruthy();
  });

  it("get_topic: unknown ID and unknown section are errors with hints", async () => {
    expect((await call("get_topic", { id: "nctb:phy:c9-10:bn:ch99" })).isError).toBe(true);
    const r = await call("get_topic", { chapter: 1, topic: "1.99" });
    expect(r.isError).toBe(true);
    expect(r.data.hint.topics).toContain("1.1");
    expect((await call("get_topic", { chapter: 40 })).isError).toBe(true);
    expect((await call("get_topic", {})).isError).toBe(true);
  });

  it("get_topic: objective, worked example and exercise IDs resolve", async () => {
    for (const id of [
      "nctb:phy:c9-10:bn:ch01:o01",
      "nctb:phy:c9-10:bn:ch01:ex:mcq01",
      catalog.books[0]!.worked_examples[0]!.id,
    ]) {
      const r = await call("get_topic", { id });
      expect(r.isError).toBe(false);
      expect(r.data.source.pdf_page).toBeGreaterThan(0);
      expect(r.data.verified).toBe(false);
    }
  });

  it("search_curriculum: Bangla and English queries", async () => {
    const bn = await call("search_curriculum", { query: "ভরবেগ" });
    expect(bn.data.hits.length).toBeGreaterThan(0);
    expect(bn.data.hits[0].id).toContain(":ch03");
    const en = await call("search_curriculum", { query: "refraction of light", version: "en" });
    expect(en.data.hits[0].id).toBe("nctb:phy:c9-10:en:ch09");
    const none = await call("search_curriculum", { query: "zzzzqqq" });
    expect(none.data.hits).toHaveLength(0);
    expect(none.data.hint).toBeTruthy();
  });

  it("get_objectives: chapter 1 Bangla", async () => {
    const { data } = await call("get_objectives", { id: "nctb:phy:c9-10:bn:ch01:t01" });
    expect(data.chapter.id).toBe("nctb:phy:c9-10:bn:ch01");
    expect(data.objectives.length).toBeGreaterThan(5);
    expect(data.objectives[0].text).toMatch(/পারব/);
  });

  it("get_exercises: pointers only, filtered by kind", async () => {
    const all = await call("get_exercises", { chapter: 1 });
    const kinds = all.data.exercises.map((e: { kind: string }) => e.kind);
    expect(kinds).toContain("mcq");
    expect(kinds).toContain("cq");
    expect(JSON.stringify(all.data)).not.toMatch(/"text"/);
    const cq = await call("get_exercises", { chapter: 1, kind: "cq" });
    expect(cq.data.exercises).toHaveLength(1);
    expect(cq.data.exercises[0].items[0].parts).toEqual(["ক", "খ", "গ", "ঘ"]);
    expect(cq.data.worked_examples).toBeUndefined();
  });
});
