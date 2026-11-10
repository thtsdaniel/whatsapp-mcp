#!/usr/bin/env bash
# Regenerates docs/changes-from-upstream.diff: every line of upstream's source
# that this copy changed or removed. Run it after any change to a file upstream
# also has. Files that exist only here (tests, scripts, CI, docs) are not in the
# diff; CHANGELOG.md lists them. go.sum and uv.lock are left out as noise.
#
# Usage: scripts/make-upstream-diff.sh
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=7d6a06dcdce1f01dfb24f60e1030d5efba9f3b88
OUT=docs/changes-from-upstream.diff
FILES="
whatsapp-bridge/main.go
whatsapp-bridge/go.mod
whatsapp-mcp-server/main.py
whatsapp-mcp-server/whatsapp.py
whatsapp-mcp-server/audio.py
whatsapp-mcp-server/pyproject.toml
.gitignore
LICENSE
"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

git clone --quiet https://github.com/lharries/whatsapp-mcp.git "$tmp/upstream"
git -C "$tmp/upstream" checkout --quiet "$BASE"

: > "$OUT"
for f in $FILES; do
  if [ -f "$f" ]; then
    diff -u --label "upstream/$f" --label "ours/$f" "$tmp/upstream/$f" "$f" >> "$OUT" || true
  else
    diff -u --label "upstream/$f" --label "ours/$f (deleted)" "$tmp/upstream/$f" /dev/null >> "$OUT" || true
  fi
done

echo "Wrote $OUT ($(wc -l < "$OUT" | tr -d ' ') lines) against upstream $BASE"
