# Distributed Chat (Course Project)

A TCP socket chat system with a custom line-oriented text protocol, a Tkinter GUI client, server-side command handling, an optional OpenAI-compatible chat API, a group chat bot, networked tic-tac-toe, and AI image fetch via Pollinations.

## Features

### Core

- Multi-client `server.py` with JSON-per-line framing (`protocol.py`)
- Tkinter client (`gui_client.py`): per-conversation buffers, group and direct chat, online user list
- Separate login window: host, port, display name, connection status; main window sidebar lists **Group Chats** and **Online Friends** only
- **Connection** button on the main chat header (right): reopens the login window after it was closed (closing the login window hides it; it does not disconnect an active session)
- Disconnect and `/quit`-style commands
- Group and direct messages, emoji shortcut buttons
- Outbound sentiment tags (rules or API)
- Server-side group bot, personality, `@bot` mentions
- Commands: `/who`, `/summary`, `/summary_nlp`, `/keywords`, `/image`, `/sentiment`, bot commands
- Optional networked tic-tac-toe
- Optional OpenAI-compatible API; without keys, a local rule-based bot and sentiment fallback apply

Image generation is performed on the **server** (Pollinations over HTTPS, bytes validated), then sent inside protocol messages as Base64. The client needs **Pillow** to open a window and show the image.

## Protocol and robustness

- Each message is one UTF-8 JSON object terminated by `\n`.
- Encoded size per message is capped by `MAX_MESSAGE_BYTES` (default 4 MiB); `encode_message` raises `ProtocolError` if exceeded.
- On decode:
  - UTF-8 or JSON failures yield a `protocol_error` message with a short, human-readable `content` (not a single generic sentence).
  - If the JSON root is not an object, a `protocol_error` is emitted instead of silently dropping the line.
- The GUI receive thread, on `ProtocolError` (e.g. buffer or line too large), enqueues a system line before tearing down the connection so failures are visible in the chat area.
- The server prints to standard output when a client handler exits with `ProtocolError` / `OSError`, and when `broadcast` skips a send because `encode_message` raised `ProtocolError`.

## GUI usage

1. After starting `gui_client.py`, a **Login — Distributed Chat** window opens in addition to the main window.
2. Set Host, Port, and Name, then click **Login** (same `login` wire format as before).
3. Sidebar: **Group Chats** and **Online Friends** only; pick a room or user to switch conversations.
4. Closing the login window hides it; use **Connection** on the main header to show it again when changing host/port or disconnecting.
5. Image messages that cannot be rendered or have an empty payload append a system line in the current conversation and show a dialog when appropriate.

## How to run

**Server (start first):**

```bash
python server.py
```

Default bind: `0.0.0.0:5001`. On Windows PowerShell:

```powershell
python server.py
```

**Clients (one or more):**

```bash
python gui_client.py
```

In the login window, set Host to `127.0.0.1` for localhost or the server LAN IP; default port is `5001`.

## Installation

The core chat path uses the Python standard library. Recommended extras:

```bash
pip install Pillow certifi
```

- **Pillow**: client displays `/image` payloads; server validates downloaded bytes as an image.
- **certifi**: supplements CA bundles on non-Windows; on Windows, if the OS trust store path fails TLS, a second attempt uses certifi when it is installed.

Optional richer sentiment:

```bash
pip install textblob
```

## Networking and image generation (including Windows)

The server fetches `https://image.pollinations.ai` over HTTPS with:

- **System proxy**: `urllib.request.getproxies()` honors `HTTP_PROXY`, `HTTPS_PROXY`, and OS proxy settings (common on Windows).
- **TLS**: On Windows, `ssl.create_default_context()` uses the OS certificate store first, which helps behind corporate proxies whose roots are only in the system store; on other platforms, certifi is loaded when available.
- **Timeout**: 90 seconds per image request to tolerate slow proxy paths.

If SSL still fails or the proxy returns an HTML block page, the server surfaces errors as chat system messages to the client that issued `/image`; client-side protocol issues appear as system lines or `protocol_error` text where applicable.

**Note**: A single frame cannot exceed `MAX_MESSAGE_BYTES`; oversized raw images are rejected with a clear server message instead of being forced through `encode_message`.

## Optional: OpenAI-compatible API

Set environment variables **before** starting the server and clients, for example:

```bash
export OPENAI_API_KEY="your_key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o-mini"
```

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="your_key"
$env:OPENAI_BASE_URL="https://api.openai.com/v1"
$env:OPENAI_MODEL="gpt-4o-mini"
```

Without keys, the group bot uses local rules; see `chatbot.py`.

## Optional: DeepSeek

Example OpenAI-compatible variables:

```powershell
$env:DEEPSEEK_API_KEY="your_deepseek_key"
$env:AI_BASE_URL="https://api.deepseek.com"
$env:AI_MODEL="deepseek-chat"
```

## Repository layout

| File | Role |
|------|------|
| `server.py` | Chat server, commands, game, image pipeline |
| `gui_client.py` | Tkinter client |
| `protocol.py` | Encode, decode, size limits |
| `chatbot.py` | Bot, sentiment, NLP helpers, Pollinations fetch |
| `system_structure.md` | Architecture and robustness notes |
| `presentation_outline.md` | Suggested demo outline |

## Demo checklist

1. Start `server.py`, then at least two `gui_client.py` instances with different names.
2. Exchange group messages; confirm send/receive and sentiment tags.
3. Select an online friend in the sidebar and send a direct message.
4. Use toolbar **Who**, **Summary**, **Summary NLP**, **Keywords**.
5. Use **Generate Image** or `/image <prompt>`; confirm server generation and client display (Pillow required).
6. **Invite Bot**, ask with `@bot`, **Bot Personality**, **Ask Bot**.
7. Open **Game** on two clients; match, move, and endgame behavior.
8. If required by the course, show tooling or documentation used during development.

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Immediate disconnect with a Protocol-related system line | Read the exact text; often line or buffer exceeded `MAX_MESSAGE_BYTES`. |
| Image always fails on Windows | Proxy and firewall; install `certifi` and retry; read server console and `Image` system lines in chat. |
| No image window | Install Pillow; check for empty-payload or display-error messages. |
| Bot never uses the cloud | Ensure variables are set in the **same shell** that launches `server.py`. |
