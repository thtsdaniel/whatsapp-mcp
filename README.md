# whatsapp-mcp (read-only)

[![ci](https://github.com/thtsdaniel/whatsapp-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/thtsdaniel/whatsapp-mcp/actions/workflows/ci.yml)

A WhatsApp MCP server that can read your chats and cannot send anything. It runs entirely on your machine, listens on `127.0.0.1` only, and works with any MCP client (Claude Code, Claude Desktop, Cursor and others).

It is a patched copy of [lharries/whatsapp-mcp](https://github.com/lharries/whatsapp-mcp). The send code is deleted, not switched off, so there is no flag or setting that brings it back.

## Why this exists

The original project is the best-known WhatsApp MCP server, and it has not had a code change since April 2025. Three problems are still open there:

- It no longer connects. WhatsApp rejects its pinned client library with `Client outdated (405)` ([#237](https://github.com/lharries/whatsapp-mcp/issues/237)).
- Its local API listens on every network interface with no authentication, so anyone on the same wifi can send messages from your account and download your media ([#215](https://github.com/lharries/whatsapp-mcp/issues/215)).
- `/api/send` reads any file path it is given, which lets a caller pull arbitrary files off your disk ([#241](https://github.com/lharries/whatsapp-mcp/issues/241)).

Sending is also the dangerous half of a WhatsApp agent. Every message you receive is text written by someone else, and your agent reads it. With a send tool in reach, one poisoned message can tell the agent to forward your chats to a stranger. With no send tool, that route does not exist.

## What changed from upstream

| | Upstream | This copy |
| --- | --- | --- |
| Connects to WhatsApp today | No, fails with 405 | Yes, current [whatsmeow](https://github.com/tulir/whatsmeow) |
| Send message, file, voice note | 3 MCP tools and `/api/send` | Deleted |
| Local API | Every interface, no auth | `127.0.0.1` only, loopback `Host` and JSON body required |
| Message store access from the MCP server | Read-write | Opened read-only (`mode=ro`) |
| Media download | 403 on every file ([#344](https://github.com/lharries/whatsapp-mcp/issues/344)) | Works |
| Attachment saved under a sender-supplied name | Path used as given | Reduced to its base name |
| Photos sent in the same second | Overwrite each other | Each saved under its message ID |
| Newer "@lid" chats | Show a bare number ([#266](https://github.com/lharries/whatsapp-mcp/issues/266)) | Show the contact name |
| Tool output | Can corrupt the MCP stream (prints to stdout) | Diagnostics go to stderr |

Every line of upstream's source that was changed or removed is in [`docs/changes-from-upstream.diff`](docs/changes-from-upstream.diff), generated against upstream commit `7d6a06d` by `scripts/make-upstream-diff.sh`, so you can regenerate it and compare. Upstream's own README is kept at [`docs/UPSTREAM-README.md`](docs/UPSTREAM-README.md). The dated list, including the files that are new here, is in [`CHANGELOG.md`](CHANGELOG.md).

## Check the claims yourself

You should not take a stranger's word for what touches your WhatsApp account. One script proves the read-only and loopback claims from the source, and CI runs it on every push:

```bash
scripts/verify-readonly.sh
```

It fails if the bridge calls anything on the WhatsApp client outside a fixed list (connect, disconnect, download, read group info), if a second HTTP route appears, if the listener leaves `127.0.0.1`, if the MCP server opens a database without `mode=ro` or writes SQL, or if the tool list is anything other than the nine read tools below.

Once the bridge is running you can also confirm what it listens on:

```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN
```

## Tools

| Tool | What it returns |
| --- | --- |
| `search_contacts` | Contacts matching a name or phone number |
| `list_chats` | Chats, newest first or by name, with the last message |
| `get_chat` | One chat by its ID |
| `get_direct_chat_by_contact` | The one-to-one chat for a phone number |
| `get_contact_chats` | Every chat a contact appears in |
| `list_messages` | Messages filtered by chat, sender, date or text, with surrounding context |
| `get_message_context` | The messages before and after one message |
| `get_last_interaction` | The most recent message with a contact |
| `download_media` | Saves a message's image, video, audio or document locally and returns the path |

## How it works

Two processes on your machine.

1. **Bridge** (`whatsapp-bridge/`, Go). Logs in to WhatsApp as a linked device through whatsmeow, the same mechanism as WhatsApp Web. It receives the history sync and every new message and writes them to `store/messages.db` (SQLite). The linked-device session lives in `store/whatsapp.db`. Once connected it serves one HTTP route on `127.0.0.1:8080`: `POST /api/download`, which fetches an attachment into `store/<chat>/`.
2. **MCP server** (`whatsapp-mcp-server/`, Python). Your MCP client launches it over stdio. It reads `messages.db` read-only and calls `/api/download` for attachments. To show real names for newer "@lid" chats it also reads two tables of `whatsapp.db` read-only (the LID-to-phone map and contact names).

The only outside service is WhatsApp itself, reached by the bridge. Nothing else is called and nothing is sent to any third party.

## Setup

You need [Go](https://go.dev/dl/) 1.26 or newer with a C compiler (the SQLite driver uses cgo), and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/thtsdaniel/whatsapp-mcp.git
cd whatsapp-mcp/whatsapp-bridge
go build -o whatsapp-bridge .
./whatsapp-bridge
```

The first run prints a QR code. On your phone open WhatsApp, go to Settings, Linked devices, Link a device, and scan it. Leave the bridge running; the history sync fills the store over a few minutes. Later runs need no QR.

Then install the MCP server's dependencies:

```bash
cd ../whatsapp-mcp-server
uv sync
```

### Connect it to your client

Claude Code:

```bash
claude mcp add whatsapp -s user -- uv --directory /absolute/path/to/whatsapp-mcp/whatsapp-mcp-server run main.py
```

Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS) and Cursor (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/whatsapp-mcp/whatsapp-mcp-server",
        "run",
        "main.py"
      ]
    }
  }
}
```

Restart the client. There are no environment variables and no API keys.

### Platforms

Used on macOS (Apple silicon), and built and tested on Linux in CI. Windows is untested here; upstream's notes on enabling cgo there are in [`docs/UPSTREAM-README.md`](docs/UPSTREAM-README.md).

## What this does not protect you from

Read-only removes the worst outcome. It does not make reading your chats risk-free.

- **Prompt injection still exists.** A message can still try to steer your agent. It cannot make this server send anything, but if your agent has other tools that reach the outside world (web requests, email, a shell), a poisoned message could try to use those. The server tells the client that message text is data and not instructions, which is a hint to the model and not a guarantee.
- **Your chats sit in plain SQLite.** `whatsapp-bridge/store/` holds every synced message unencrypted, and `whatsapp.db` holds the session of a device linked to your account. Anyone who can read that folder can read your chats, and a copied session could act as your linked device. Keep it off shared machines and out of backups you do not control.
- **The bridge prints messages to its terminal.** Each incoming message is logged as it arrives.
- **WhatsApp can flag unofficial clients.** This uses the linked-device protocol through a third-party library, which WhatsApp does not support and may treat as a breach of its terms. Never sending lowers the profile and does not remove the risk. If your account is flagged, unlink the device and stop.
- **Any program on your machine can call the download route.** It is not reachable from the network or from a web page, but local software can ask the bridge to save an attachment into the store. That route cannot send, delete or read anything back.

## Runbook

- **Keep it running.** New messages arrive only while the bridge is up. Run it in a terminal tab, tmux, or your service manager of choice. When it stops, reads still work from the store and it back-fills on the next start.
- **Restart.** Ctrl+C the bridge and run `./whatsapp-bridge` again from `whatsapp-bridge/`. It must be started from that folder, because the store path is relative.
- **`Client outdated (405)`.** WhatsApp moved past the pinned whatsmeow. Run `go get go.mau.fi/whatsmeow@latest && go mod tidy`, fix any new arguments `go vet ./...` reports, rebuild, then run `scripts/verify-readonly.sh`.
- **A download fails with 403.** The media link expired on WhatsApp's side, which happens with old messages. It cannot be fixed from here.
- **Tools return nothing.** The bridge has not run or has not finished syncing. Check that `whatsapp-bridge/store/messages.db` exists.
- **Unlink and wipe.** On the phone: Linked devices, tap the device, Log out. Then delete `whatsapp-bridge/store/` to remove the local copy of every chat.

## Development

```bash
cd whatsapp-bridge && go vet ./... && go test ./... && go build -o whatsapp-bridge .
cd ../whatsapp-mcp-server && uv run python test_tools.py
cd .. && scripts/verify-readonly.sh
```

Pull requests are welcome for fixes and for keeping up with WhatsApp. A change that adds a send path, a write to the store from the MCP server, or a listener off loopback will not be merged; the script above is there to catch one by accident.

Security reports: see [`SECURITY.md`](SECURITY.md).

## Credits and licence

MIT, see [`LICENSE`](LICENSE). The original work is [whatsapp-mcp](https://github.com/lharries/whatsapp-mcp) by Luke Harries, and the WhatsApp protocol library is [whatsmeow](https://github.com/tulir/whatsmeow) by Tulir Asokan. The fix for media downloads follows the approach of upstream PR #361, and the working whatsmeow version was the one verified in upstream issue [#382](https://github.com/lharries/whatsapp-mcp/issues/382).

This project is not affiliated with, endorsed by or connected to WhatsApp or Meta. You use it with your own account at your own risk.
