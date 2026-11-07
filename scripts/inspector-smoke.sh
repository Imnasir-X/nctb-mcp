#!/bin/bash
# Exercise every tool through the MCP Inspector CLI against the built server.
# Usage: scripts/inspector-smoke.sh [path-to-mcp-inspector]  (default: npx @modelcontextprotocol/inspector)
set -u
INSPECTOR=${1:-"npx -y @modelcontextprotocol/inspector"}
run() {
  echo "### $*"
  out=$($INSPECTOR --cli node dist/cli.js "$@" 2>/dev/null)
  echo "bytes: ${#out}"
  echo "$out" | head -c 1500
  echo; echo
}
run --method tools/list
run --method tools/call --tool-name list_chapters
run --method tools/call --tool-name list_chapters --tool-arg version=en
run --method tools/call --tool-name get_topic --tool-arg chapter=3
run --method tools/call --tool-name get_topic --tool-arg chapter=3 --tool-arg topic=3.4 --tool-arg version=en
run --method tools/call --tool-name get_topic --tool-arg id=nctb:phy:c9-10:bn:ch01:t05
run --method tools/call --tool-name search_curriculum --tool-arg query=ভরবেগ
run --method tools/call --tool-name search_curriculum --tool-arg "query=refraction of light" --tool-arg version=en
run --method tools/call --tool-name get_objectives --tool-arg chapter=9
run --method tools/call --tool-name get_exercises --tool-arg chapter=1 --tool-arg kind=cq
run --method tools/call --tool-name get_topic --tool-arg id=nctb:phy:c9-10:bn:ch99
