# Changelog

Format: Keep a Changelog. Base: lharries/whatsapp-mcp at `7d6a06dcdce1f01dfb24f60e1030d5efba9f3b88`.

## [Unreleased]

### Added

### Changed

### Fixed

## [1.0.0] - 2026-11-10

First public release. Everything below is measured against the upstream base commit.

### Added

- MCP server instructions telling the client that message text is third-party data, not instructions.
- `scripts/verify-readonly.sh`: fails when the bridge calls anything on the WhatsApp client outside a fixed read-only list, when a second HTTP route appears, when the listener leaves `127.0.0.1`, when the MCP server opens a database without `mode=ro` or writes SQL, or when the tool list is not the nine read tools. 2026-11-10.
- Bridge tests (`whatsapp-bridge/main_test.go`) for attachment file names, the media direct path and the request guards. 2026-11-10.
- CI (`.github/workflows/ci.yml`): gofmt, `go vet`, `go test`, build, and the read-only script. 2026-11-10.
- `SECURITY.md`. 2026-11-10.
- Docs: AGENTS.md, README.md, EXPLAINER.md, CHANGELOG.md; `docs/changes-from-upstream.diff`; upstream README moved to `docs/UPSTREAM-README.md`.
- `.gitignore` entries for the bridge binaries and `whatsapp-bridge/store/`.

### Changed

- Bumped `go.mau.fi/whatsmeow` to `v0.0.0-20261017175727-b2b1e71d45e2` and `go-sqlite3` to `v1.14.52`; passed `context.Context` to `Download`, `sqlstore.New`, `GetFirstDevice`, `GetGroupInfo`, `Contacts.GetContact`.
- Bridge HTTP server binds `127.0.0.1:8080` instead of every interface.
- `POST /api/download` refuses a request whose `Host` is not a loopback name (403) or whose `Content-Type` is not `application/json` (415), so a web page cannot reach it through DNS rebinding or a cross-origin form post. 2026-11-10.
- MCP server opens `messages.db` read-only (`mode=ro`) and calls the bridge on `127.0.0.1`.
- The attachment file-name logic moved into `safeMediaFilename` and the route into `downloadHandler`, with no change in behaviour, so both can be tested. 2026-11-10.
- README, AGENTS.md and EXPLAINER.md rewritten for public readers. 2026-11-10.

### Removed

- Bridge: `/api/send`, `sendWhatsAppMessage`, the unused `requestHistorySync`, and the voice-note helpers (`analyzeOggOpus`, `placeholderWaveform`, `min`).
- MCP: `send_message`, `send_file`, `send_audio_message` tools and their helpers; `audio.py`.
- The bridge's "Type 'help' for commands" line; it has no commands. 2026-11-10.

### Fixed

- `Client outdated (405)` on connect (upstream #237, #382).
- Media download 403: the signed query string is kept in the direct path (upstream #344, approach of PR #361).
- Path traversal on media save: a sender-supplied document name like `../../x` now keeps only its base name.
- Media saved under the same second overwrote each other: stored names are `image_<YYYYMMDD_HHMMSS>.jpg`, so of four photos sent in two seconds only two were ever saved, and a download of the other two returned the cached file. `download_media` now prefixes the message ID (`<messageID>_image_....jpg`). Files saved before this fix keep their old names. 2026-10-30.
- Arbitrary file read through `/api/send` `media_path` (upstream #241), by removing the route.
- `list_chats(include_last_message=False)` selected message columns without the join and always returned nothing; it now selects NULLs.
- Diagnostics in `whatsapp.py` printed to stdout, which carries the MCP protocol; they go to stderr through `_log`.
- Chats and senders on newer "@lid" ids showed a bare number (upstream #266): names now resolve at read time through the session store's `whatsmeow_lid_map` and `whatsmeow_contacts` (opened read-only), falling back to `+phone`.
