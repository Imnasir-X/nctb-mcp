# Owner decisions — nctb-mcp publishing

Dated 2026-11-13, recorded by the maintainer (Nasir Khan) so the npm release is unblocked. Each decision lists
its follow-ups; revisit them if NCTB or the law changes.

## 1. Headings and learning-objective lines

**Decision: ship them.** Chapter/section headings and the chapter learning-objective lines are short, factual
navigational text. They are included so students and teachers can find the right page of the official PDF — the
package never ships body text, worked-example text, or exercise/question text, and every item points to the
official source.

- Basis: short factual quotation for locating the authoritative copy; no substitution for the book is possible
  through this package.
- Follow-up: send a permission/courtesy letter to NCTB describing the project and this data boundary.
- Follow-up: if NCTB requests removal of any line, remove it immediately and note it in the changelog.

## 2. Licence of the metadata compilation

**Decision: CC BY 4.0 for the compilation** (`data/*.json` — IDs, page pointers, structure, bn/en pairing, review
flags). Attribution: the nctb-mcp project (https://github.com/Imnasir-X/nctb-mcp).

- Code remains **MIT** (see LICENSE).
- Textbook text and images remain © NCTB ("All rights reserved by the Publisher") and are **not** licensed here;
  DATA_LICENSE.md carries the notice.

## 3. npm release

**Decision: publish `nctb-mcp@0.1.0`** once the release checklist below is done. The README's `npx -y nctb-mcp`
instructions become real at that point.

- Follow-up (maintainer): create an npm granular access token and add it as the `NPM_TOKEN` Actions secret at
  https://github.com/Imnasir-X/nctb-mcp/settings/secrets/actions.
- Follow-up (maintainer): enable "Allow GitHub Actions to create and request pull requests"
  (Settings > Actions > General), then run the Release workflow once (workflow_dispatch) to publish.
- Follow-up: after the first publish, verify `npx -y nctb-mcp --help` starts and the server appears in
  `npm search nctb`.
- Follow-up: submit the server to the MCP directories (Smithery, Glama, mcpservers.org) with the BanglaEdu Bench
  cross-link.
