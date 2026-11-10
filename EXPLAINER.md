# WhatsApp reader for AI assistants

Last verified: 2026-11-10

## What this is

A small program for your own computer that lets an AI assistant such as Claude read your WhatsApp chats. It logs in the same way WhatsApp Web does, by scanning a code with your phone, and keeps a copy of your messages on your computer. The assistant can search and read that copy. It has no way to send a message, react, or mark anything as read; that part was removed from the program on purpose, so no setting can turn it back on.

## Who uses it and for what

Anyone who wants their assistant to know what was said on WhatsApp: finding an address someone sent, catching up on a group, checking what a client asked for. Nobody else sees anything. No money runs through it.

## Where it lives

Only on your own computer, in the folder you downloaded it to. There is no website, no online database and no account other than your own WhatsApp number. The copy of your chats sits in a folder called "store" next to the program.

## What it costs and who pays

Nothing. It is free, open software under the MIT licence, running on your own machine.

## How to check it is alive

The terminal window running the program says "Connected to WhatsApp" and prints new messages as they arrive. On your phone, WhatsApp, Settings, Linked devices shows it as a linked device. In your assistant, asking for your recent WhatsApp chats returns them.

## If it breaks

- It says "client outdated": WhatsApp changed something and the program needs a newer version of the part that talks to WhatsApp. The README has the three commands that update it.
- The assistant finds no messages: the program is not running, or it has not finished its first sync. Start it again in a terminal and give it a few minutes.
- A file or photo will not download: old attachments expire on WhatsApp's side. Nothing to fix.
- WhatsApp flags your account: unlink the device on your phone straight away and stop using this.

## How to leave

1. On your phone: WhatsApp, Settings, Linked devices, tap this device, Log out.
2. Stop the program.
3. Delete the "store" folder; it holds the copy of every chat.
4. Remove it from your assistant's connected tools.

Nothing else to cancel.

## History

- 2025: The original WhatsApp MCP project is published by Luke Harries. It can read and send.
- April 2025: The original gets its last code change. Over the following year it stops being able to connect, and two security problems are reported and left open.
- 2026-10-21: This copy is made. Sending is removed, it is made to listen only on the computer it runs on, and it is updated so it connects again. Contact names that showed as bare numbers are fixed.
- 2026-10-30: Photos sent in the same second no longer overwrite each other.
- 2026-11-10: Prepared for public release. Tests, an automatic check that sending has not come back, and a guard that stops web pages from reaching the program are added.

## Where the technical docs are

README.md (setup, what changed, what it does not protect you from), AGENTS.md (rules for an AI agent working on the code), CHANGELOG.md (dated changes), SECURITY.md (how to report a problem), docs/changes-from-upstream.diff (every changed line against the original).
