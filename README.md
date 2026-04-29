# Distributed Chat Final Project

This project is a socket-based distributed chat system with a Tkinter GUI client.
It includes the compulsory GUI topic, a chatbot selective topic, and several small
bonus features.

## Features

- Socket server with multiple clients
- WeChat-style Tkinter GUI client
- Real-time send and receive display
- Login username
- Disconnect button and `/quit` command
- Online friend list and direct messages
- Public group chat
- Interactive multiplayer Tic-Tac-Toe game
- Emoji shortcut buttons
- API-based sentiment tags for outgoing messages, such as Happy, Excited,
  Confused, Worried, Sad, Angry, Bug/Problem, or Neutral
- Server-side group chatbot with context and editable personality
- Chatbot group interaction with `@bot` mention
- Chat history commands:
  - `/who`
  - `/summary`
  - `/keywords`
  - `/bot join`
  - `/bot leave`
  - `/bot status`

The chatbot and sentiment classifier can use an OpenAI-compatible API when
environment variables are set. If no API key is available, the demo falls back to
local rule-based chatbot and sentiment behavior.

## Files

- `server.py`: multi-client socket chat server
- `gui_client.py`: Tkinter GUI chat client
- `protocol.py`: JSON-line message encoding and decoding
- `chatbot.py`: chatbot and sentiment logic
- `system_structure.md`: system structure and robustness explanation
- `presentation_outline.md`: suggested video and slide structure

## How to Run

Open one terminal for the server:

```powershell
python server.py
```

Open one or more other terminals for clients:

```powershell
python gui_client.py
```

In each GUI window:

1. Enter a username.
2. Click `Connect`.
3. Select `Public Chat` or an online friend in the left sidebar.
4. Send messages.
5. Test `Who`, `Summary`, `Keywords`, emoji buttons, `Invite Bot`, `Ask Bot`, and `Game`.
6. Send a message like `@bot explain this project` to show group interaction.
7. Click `Disconnect` or type `/quit` to leave the chat.

## Optional ChatGPT API Configuration

The chatbot supports the ChatGPT API, DeepSeek API, and other OpenAI-compatible
APIs. It sends chat history to a Chat Completions style endpoint:

```text
POST https://api.openai.com/v1/chat/completions
Authorization: Bearer OPENAI_API_KEY
```

Configure it with environment variables before starting the server and GUI:

```powershell
$env:OPENAI_API_KEY="your_key"
$env:OPENAI_BASE_URL="https://api.openai.com/v1"
$env:OPENAI_MODEL="gpt-4o-mini"
python server.py
```

If your class-provided API or pi-mono API uses an OpenAI-compatible endpoint, set
`OPENAI_BASE_URL`, `OPENAI_API_KEY`, and `OPENAI_MODEL` to those values instead.

## Optional DeepSeek API Configuration

DeepSeek uses an OpenAI-compatible API format. Configure these environment
variables before starting the server and GUI:

```powershell
$env:DEEPSEEK_API_KEY="your_deepseek_key"
$env:AI_BASE_URL="https://api.deepseek.com"
$env:AI_MODEL="deepseek-chat"
python server.py
```

You can also save the DeepSeek key permanently for the current Windows user:

```powershell
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", "your_deepseek_key", "User")
[Environment]::SetEnvironmentVariable("AI_BASE_URL", "https://api.deepseek.com", "User")
[Environment]::SetEnvironmentVariable("AI_MODEL", "deepseek-chat", "User")
```

## Demo Checklist

- Start `server.py`.
- Start two GUI clients with different names.
- Send messages from both clients and show both sent and received messages.
- Click an online friend in the left sidebar and send a direct message.
- Use emoji buttons.
- Show detailed API-based sentiment labels beside messages.
- Click `Who`.
- Send several chat messages, then click `Summary` and `Keywords`.
- Click `Invite Bot`, mention `@bot`, and show the bot replying to the whole group.
- Click `Bot Personality`, set a personality, then use `Ask Bot`.
- Click `Game` in two different clients, join Tic-Tac-Toe, and show turns, board sync, and win/draw detection.
- Show pi-mono usage during development, such as code generation, debugging, or
  documentation support.
