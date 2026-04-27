# Distributed Chat Final Project

This project is a socket-based distributed chat system with a Tkinter GUI client.
It includes the compulsory GUI topic, a chatbot selective topic, and several small
bonus features.

## Features

- Socket server with multiple clients
- WeChat-style Tkinter GUI client
- Real-time send and receive display
- Login username
- Online friend list and direct messages
- Public group chat
- Interactive multiplayer Tic-Tac-Toe game
- Emoji buttons
- Sentiment tag for outgoing messages: Positive, Neutral, or Negative
- Server-side group chatbot with context and editable personality
- Chat history commands:
  - `/who`
  - `/summary`
  - `/keywords`
  - `/bot join`
  - `/bot leave`
  - `/bot status`

The chatbot can use an OpenAI-compatible API when environment variables are set.
If no API key is available, it falls back to a local rule-based bot so the demo
still works.

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

## Optional API Configuration

The chatbot supports OpenAI-compatible APIs:

```powershell
$env:OPENAI_API_KEY="your_key"
$env:OPENAI_BASE_URL="https://api.openai.com/v1"
$env:OPENAI_MODEL="gpt-4o-mini"
python gui_client.py
```

If your class-provided API or pi-mono API uses an OpenAI-compatible endpoint, set
`OPENAI_BASE_URL`, `OPENAI_API_KEY`, and `OPENAI_MODEL` to those values.

## Demo Checklist

- Start `server.py`.
- Start two GUI clients with different names.
- Send messages from both clients and show both sent and received messages.
- Click an online friend in the left sidebar and send a direct message.
- Use emoji buttons.
- Show sentiment labels beside messages.
- Click `Who`.
- Send several chat messages, then click `Summary` and `Keywords`.
- Click `Invite Bot`, mention `@bot`, and show the bot replying to the whole group.
- Click `Bot Personality`, set a personality, then use `Ask Bot`.
- Click `Game` in two different clients, join Tic-Tac-Toe, and show turns, board sync, and win/draw detection.
- Show pi-mono usage during development, such as code generation, debugging, or
  documentation support.
