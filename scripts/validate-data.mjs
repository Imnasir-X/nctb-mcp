// Validate every bundled book file against the JSON Schema.
import { readFileSync, readdirSync } from "node:fs";
import Ajv2020 from "ajv/dist/2020.js";

const schema = JSON.parse(readFileSync("data/schema/nctb-data.schema.json", "utf8"));
const validate = new Ajv2020({ allErrors: true, strict: false }).compile(schema);
let bad = 0;
for (const f of readdirSync("data").filter((x) => /-(bn|en)\.json$/.test(x))) {
  const ok = validate(JSON.parse(readFileSync(`data/${f}`, "utf8")));
  console.log(`${ok ? "ok  " : "FAIL"} ${f}`);
  if (!ok) {
    bad++;
    console.log(JSON.stringify(validate.errors?.slice(0, 10), null, 1));
  }
}
process.exit(bad ? 1 : 0);
