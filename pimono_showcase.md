# Pi-mono AI Code Assistant Showcase

## What I Asked Pi-mono

I used pi-mono inside this project folder with the local Ollama model:

```powershell
pi --provider ollama-local --model phi4-mini:latest
```

Example task:

```text
Explain how the sentiment analysis feature works in this Python socket chat project.
Mention the GUI button, server command, and chatbot.py logic.
```

## What Pi-mono Helped With

Pi-mono helped me inspect and document the sentiment analysis workflow:

- In `gui_client.py`, the **Analyze Sentiment** button is created in `build_chat_panel`.
- The button calls `analyze_sentiment_dialog`.
- `analyze_sentiment_dialog` asks the user for input text and sends `/sentiment <text>` to the server.
- In `server.py`, `handle_command` handles commands that start with `/sentiment `.
- The server calls `analyze_sentiment_textblob(text)` from `chatbot.py`.
- The server sends the result back as a system message, for example:

```text
Sentiment: Excited :D (Source: api)
```

## Demo Script

I used pi-mono as an AI code assistant to understand and verify the sentiment analysis feature. It helped trace the workflow from the GUI button in `gui_client.py`, to the `/sentiment` command handler in `server.py`, and finally to the sentiment logic in `chatbot.py`.

The feature works in two ways. First, the **Analyze Sentiment** button lets the user enter text, sends it to the server, and displays a result like `Sentiment: Excited :D`. Second, normal chat messages are automatically tagged with a sentiment label before being sent.

## Live Demo Steps

1. Start the chat project.
2. Log in to the GUI client.
3. Click **Analyze Sentiment**.
4. Enter:

```text
I am very happy and excited about this project
```

5. Show the result in the chat area:

```text
Sentiment: Excited :D (Source: api)
```

6. Open pi-mono in the terminal and show that it was used to explain or inspect the project:

```powershell
pi --provider ollama-local --model phi4-mini:latest
```

Then ask:

```text
Explain how the sentiment analysis feature works in this project.
```

