# Security

This project exists because of security problems in the project it was copied from, so reports are taken seriously.

## Reporting a problem

Please do not open a public issue for a vulnerability. Use GitHub's private reporting instead: on the repository page open the **Security** tab and choose **Report a vulnerability**. Include what you did, what happened, and the commit you tested.

## What counts

- Any way to make the bridge or the MCP server send a message, upload a file, mark a chat as read or otherwise change anything on the WhatsApp account.
- Any way to reach the bridge's HTTP route from another machine or from a web page.
- Any way to make the bridge write a file outside `whatsapp-bridge/store/`, or to make the MCP server write to either database.
- Any way to read the linked-device session keys through an MCP tool.

## What is known and documented

These are limits of the design, listed in the README under "What this does not protect you from". They are not treated as vulnerabilities.

- Incoming messages are untrusted text that the AI client reads. Prompt injection against the client is possible; this server only guarantees that it offers nothing to send with.
- The message store and the session are unencrypted SQLite files on the local disk.
- Any local program can call the download route, which saves an attachment into the store.
- WhatsApp may flag accounts that use unofficial clients.

## Checking a build

`scripts/verify-readonly.sh` proves the read-only and loopback claims from the source. Run it on any copy you did not build yourself.
