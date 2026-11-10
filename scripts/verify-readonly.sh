#!/usr/bin/env bash
# Proves the read-only and loopback-only claims from the source itself.
# Exits 1 the moment one of them stops being true. CI runs it on every push.
#
# Usage: scripts/verify-readonly.sh
# The MCP tool check needs uv (https://docs.astral.sh/uv/); it is skipped with a
# warning when uv is not installed.
set -euo pipefail
cd "$(dirname "$0")/.."

BRIDGE=whatsapp-bridge/main.go
SERVER=whatsapp-mcp-server

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

# 1. The bridge calls only these methods on the WhatsApp client. None of them
#    sends, uploads, marks as read or changes presence.
allowed="AddEventHandler Connect Disconnect Download GetGroupInfo GetQRChannel IsConnected Store"
used=$(grep -oE 'client\.[A-Z][A-Za-z]*' "$BRIDGE" | sed 's/client\.//' | sort -u | tr '\n' ' ' | sed 's/ $//')
[ "$used" = "$allowed" ] || fail "bridge client calls changed. Expected: $allowed. Found: $used"
echo "ok  bridge client calls: $used"

# 2. No send, upload, read-receipt or presence symbol anywhere in the bridge.
if grep -nE 'SendMessage|\.Upload\(|MarkRead|SendPresence|SendChatPresence|/api/send' "$BRIDGE"; then
  fail "the bridge contains a send, upload, read-receipt or presence symbol"
fi
echo "ok  no send, upload, read-receipt or presence symbol in the bridge"

# 3. One HTTP route, and it is the download route.
routes=$(grep -c 'http\.HandleFunc(' "$BRIDGE")
[ "$routes" = "1" ] || fail "expected 1 HTTP route in the bridge, found $routes"
grep -q 'http\.HandleFunc("/api/download"' "$BRIDGE" || fail "the one HTTP route is not /api/download"
echo "ok  one HTTP route: POST /api/download"

# 4. The listener is bound to loopback and nothing else.
grep -q 'fmt\.Sprintf("127\.0\.0\.1:%d", port)' "$BRIDGE" || fail "the bridge is not bound to 127.0.0.1"
if grep -nE '0\.0\.0\.0|Sprintf\(":%d"' "$BRIDGE"; then
  fail "the bridge binds a non-loopback address"
fi
echo "ok  listener bound to 127.0.0.1"

# 5. The MCP server is two source files, opens every database read-only and
#    writes no SQL. test_tools.py is the one other file: it builds a throwaway
#    store in a temporary folder and is never loaded by the server.
sources=$(cd "$SERVER" && ls *.py | tr '\n' ' ' | sed 's/ $//')
[ "$sources" = "main.py test_tools.py whatsapp.py" ] || fail "unexpected Python files in the MCP server: $sources"
if grep -n 'sqlite3\.connect(' "$SERVER"/main.py "$SERVER"/whatsapp.py | grep -v 'mode=ro'; then
  fail "a database is opened without mode=ro"
fi
if grep -niE '\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b[^a-z]' "$SERVER"/main.py "$SERVER"/whatsapp.py | grep -viE '^\S+:\s*#|""".*"""'; then
  fail "the MCP server contains a writing SQL statement"
fi
if grep -nE 'import +test_tools|from +test_tools' "$SERVER"/main.py "$SERVER"/whatsapp.py; then
  fail "the MCP server loads the test file"
fi
echo "ok  MCP server opens the store read-only and writes no SQL"

# 6. The MCP server makes one HTTP call, to the loopback download route.
posts=$(grep -cE 'requests\.(post|put|patch|delete|get)\(' "$SERVER"/whatsapp.py)
[ "$posts" = "1" ] || fail "expected 1 HTTP call in the MCP server, found $posts"
grep -q 'WHATSAPP_API_BASE_URL = "http://127\.0\.0\.1:8080/api"' "$SERVER"/whatsapp.py || fail "the MCP server does not call the loopback bridge"
echo "ok  MCP server makes one HTTP call, to 127.0.0.1"

# 7. The MCP server exposes exactly these nine read tools.
expected="download_media get_chat get_contact_chats get_direct_chat_by_contact get_last_interaction get_message_context list_chats list_messages search_contacts"
if command -v uv >/dev/null 2>&1; then
  tools=$(uv run --quiet --directory "$SERVER" python -c "import main, asyncio; print(' '.join(sorted(t.name for t in asyncio.run(main.mcp.list_tools()))))")
  [ "$tools" = "$expected" ] || fail "MCP tools changed. Expected: $expected. Found: $tools"
  echo "ok  MCP tools: $tools"
else
  echo "warn  uv not found, skipped the MCP tool list check" >&2
fi

echo "All read-only checks passed."
