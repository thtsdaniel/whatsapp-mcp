"""Calls every MCP tool through the real MCP call path against a synthetic store.

Newer versions of the MCP library validate what a tool returns against its return
type, so a dependency bump can break every tool while the tool list still looks
fine. This test catches that. It never touches a real message store: it builds a
small one in a temporary folder and points the reader at it, and it points the
download call at a closed port.

Run: uv run python test_tools.py
"""

import asyncio
import json
import os
import sqlite3
import sys
import tempfile

import whatsapp
import main

ALICE = "15550001111@s.whatsapp.net"
LID_CHAT = "99887766554433@lid"
GROUP = "120363000000000001@g.us"


def build_store(folder: str) -> None:
    messages = sqlite3.connect(os.path.join(folder, "messages.db"))
    messages.executescript(
        """
        CREATE TABLE chats (jid TEXT PRIMARY KEY, name TEXT, last_message_time TIMESTAMP);
        CREATE TABLE messages (
            id TEXT, chat_jid TEXT, sender TEXT, content TEXT, timestamp TIMESTAMP,
            is_from_me BOOLEAN, media_type TEXT, filename TEXT, url TEXT, media_key BLOB,
            file_sha256 BLOB, file_enc_sha256 BLOB, file_length INTEGER,
            PRIMARY KEY (id, chat_jid)
        );
        """
    )
    messages.executemany(
        "INSERT INTO chats VALUES (?, ?, ?)",
        [
            (ALICE, "Alice Example", "2026-01-02 10:00:00+00:00"),
            # The bridge stores a bare number as the name of an "@lid" chat
            (LID_CHAT, "99887766554433", "2026-01-03 11:00:00+00:00"),
            (GROUP, "Test Group", "2026-01-04 12:00:00+00:00"),
        ],
    )
    messages.executemany(
        "INSERT INTO messages (id, chat_jid, sender, content, timestamp, is_from_me, media_type, filename)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("M1", ALICE, "15550001111", "hello there", "2026-01-02 09:59:00+00:00", 0, "", ""),
            ("M2", ALICE, "15550001111", "the address is 1 Test Street", "2026-01-02 10:00:00+00:00", 0, "", ""),
            ("M3", LID_CHAT, "99887766554433", "lid chat message", "2026-01-03 11:00:00+00:00", 0, "", ""),
            ("M4", GROUP, "15550001111", "group photo", "2026-01-04 12:00:00+00:00", 0, "image", "image_20260104_120000.jpg"),
            ("M5", GROUP, "me", "my reply", "2026-01-04 11:59:00+00:00", 1, "", ""),
        ],
    )
    messages.commit()
    messages.close()

    session = sqlite3.connect(os.path.join(folder, "whatsapp.db"))
    session.executescript(
        """
        CREATE TABLE whatsmeow_lid_map (lid TEXT PRIMARY KEY, pn TEXT);
        CREATE TABLE whatsmeow_contacts (
            our_jid TEXT, their_jid TEXT, first_name TEXT, full_name TEXT,
            push_name TEXT, business_name TEXT
        );
        """
    )
    session.execute("INSERT INTO whatsmeow_lid_map VALUES ('99887766554433', '15550002222')")
    session.execute(
        "INSERT INTO whatsmeow_contacts VALUES"
        " ('me@s.whatsapp.net', '15550002222@s.whatsapp.net', 'Bob', 'Bob Example', 'bob', '')"
    )
    session.commit()
    session.close()


# (tool, arguments, text that must appear in the result; None means "must not raise")
CASES = [
    ("search_contacts", {"query": "alice"}, "Alice Example"),
    ("list_chats", {}, "Test Group"),
    ("list_chats", {}, "Bob Example"),  # the "@lid" chat resolves to its contact name
    ("list_chats", {"include_last_message": False, "sort_by": "name"}, "Alice Example"),
    ("get_chat", {"chat_jid": ALICE}, "Alice Example"),
    ("get_chat", {"chat_jid": "nobody@s.whatsapp.net"}, None),
    ("get_direct_chat_by_contact", {"sender_phone_number": "15550001111"}, "Alice Example"),
    ("get_direct_chat_by_contact", {"sender_phone_number": "00000"}, None),
    ("get_contact_chats", {"jid": "15550001111"}, "Test Group"),
    ("list_messages", {"query": "address"}, "1 Test Street"),
    ("list_messages", {"query": "no-such-text"}, "No messages to display."),
    ("list_messages", {"chat_jid": GROUP, "include_context": False}, "group photo"),
    ("get_message_context", {"message_id": "M2"}, "hello there"),
    ("get_last_interaction", {"jid": "15550001111"}, "group photo"),
    ("get_last_interaction", {"jid": "nobody"}, None),
    ("download_media", {"message_id": "M4", "chat_jid": GROUP}, "Failed to download media"),
]


def as_text(result) -> str:
    def encode(value):
        return getattr(value, "text", None) or getattr(value, "__dict__", None) or str(value)

    # Tool text arrives JSON-encoded inside JSON, so undo the escaping before matching
    return json.dumps(result, default=encode).replace("\\\\", "\\").replace('\\"', '"')


async def run() -> int:
    failures = 0
    tools = sorted(tool.name for tool in await main.mcp.list_tools())
    called = sorted({name for name, _, _ in CASES})
    if called != tools:
        print(f"FAIL the cases cover {called} but the server exposes {tools}")
        failures += 1

    for name, arguments, expected in CASES:
        try:
            text = as_text(await main.mcp.call_tool(name, arguments))
        except Exception as error:  # a validation error surfaces here
            print(f"FAIL {name} {arguments}: {type(error).__name__}: {str(error)[:200]}")
            failures += 1
            continue
        if expected is not None and expected not in text:
            print(f"FAIL {name} {arguments}: expected {expected!r} in {text[:200]}")
            failures += 1
        else:
            print(f"ok   {name} {arguments}")

    print(f"{len(CASES) - failures} of {len(CASES)} tool calls passed" if failures == 0 else f"{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as store:
        build_store(store)
        whatsapp.MESSAGES_DB_PATH = os.path.join(store, "messages.db")
        whatsapp.SESSION_DB_PATH = os.path.join(store, "whatsapp.db")
        whatsapp.WHATSAPP_API_BASE_URL = "http://127.0.0.1:1/api"  # closed port, never a live bridge
        sys.exit(asyncio.run(run()))
