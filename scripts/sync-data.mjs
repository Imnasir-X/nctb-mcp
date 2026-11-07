// Copy the shared data layer into this package so `npx nctb-mcp` works offline.
// Source of truth: $NCTB_SHARED_DATA (default ../nctb-shared/data).
import { cpSync, mkdirSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";

const src = resolve(process.env.NCTB_SHARED_DATA ?? "../nctb-shared/data");
const dst = resolve("data");
mkdirSync(join(dst, "schema"), { recursive: true });
cpSync(join(src, "schema", "nctb-data.schema.json"), join(dst, "schema", "nctb-data.schema.json"));
let n = 0;
for (const dir of readdirSync(src, { withFileTypes: true })) {
  if (!dir.isDirectory() || dir.name === "schema") continue;
  for (const f of readdirSync(join(src, dir.name))) {
    if (/^[a-z0-9-]+-(bn|en)\.json$/.test(f)) {
      cpSync(join(src, dir.name, f), join(dst, f));
      n++;
    }
  }
}
cpSync(join(src, "manifest.json"), join(dst, "manifest.json"));
console.log(`synced ${n} book files from ${src}`);
