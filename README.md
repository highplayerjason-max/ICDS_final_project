# Distributed Chat Final Project

This project is a socket-based distributed chat system with a Tkinter GUI client.
It includes the compulsory GUI topic, a chatbot selective topic, and several small
bonus features.

## Features

- Socket server with multiple clients
- Tkinter GUI client
- Real-time send and receive display
- Login username
- Emoji buttons
- Sentiment tag for outgoing messages, such as Happy, Excited, Confused,
  Worried, Sad, Angry, Bug/Problem, or Neutral
- Chatbot with context and editable personality
- Chat history commands:
  - `/who`
  - `/summary`
  - `/keywords`

The chatbot can use an OpenAI-compatible API when environment variables are set.
If no API key is available, it falls back to a local rule-based bot so the demo
still works.

## Files

- `server.py`: multi-client socket chat server
- `gui_client.py`: Tkinter GUI chat client
- `protocol.py`: JSON-line message encoding and decoding
- `chatbot.py`: chatbot and sentiment logic
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
3. Send messages.
4. Test `Who`, `Summary`, `Keywords`, emoji buttons, and `Ask Bot`.

## Optional ChatGPT API Configuration

The chatbot supports the ChatGPT API and other OpenAI-compatible APIs. It sends
chat history to the Chat Completions endpoint:

```text
POST https://api.openai.com/v1/chat/completions
Authorization: Bearer OPENAI_API_KEY
```

Configure it with environment variables before starting the GUI:

```powershell
$env:OPENAI_API_KEY="your_key"
$env:OPENAI_BASE_URL="https://api.openai.com/v1"
$env:OPENAI_MODEL="gpt-4o-mini"
python gui_client.py
```

If your class-provided API or pi-mono API uses an OpenAI-compatible endpoint, set
`OPENAI_BASE_URL`, `OPENAI_API_KEY`, and `OPENAI_MODEL` to those values instead.
If no API key is configured, the GUI automatically uses the local fallback bot.

## Demo Checklist

- Start `server.py`.
- Start two GUI clients with different names.
- Send messages from both clients and show both sent and received messages.
- Use emoji buttons.
- Show detailed sentiment labels beside messages.
- Click `Who`.
- Send several chat messages, then click `Summary` and `Keywords`.
- Click `Bot Personality`, set a personality, then use `Ask Bot`.
- Show pi-mono usage during development, such as code generation, debugging, or
  documentation support.
