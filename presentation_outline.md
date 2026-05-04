# Presentation Outline

Target length: 10-15 minutes.

## 1. Introduction

- Project goal: upgrade a terminal socket chat system into a GUI chat application.
- Motivation: make the system closer to real chat apps with buttons, real-time display,
  chatbot support, and analysis features.
- Architecture overview:
  - `server.py` accepts multiple socket clients.
  - `gui_client.py` connects to the server and renders messages with Tkinter.
  - `protocol.py` keeps messages structured using JSON lines.
  - `chatbot.py` handles bot replies and sentiment analysis.

## 2. Demo

- Run the server.
- Open two GUI clients.
- Connect with two different usernames.
- Send messages from both clients.
- Show that each client displays both sent and received messages.
- Use emoji buttons.
- Show API-based sentiment tags such as `[Happy]`, `[Confused]`,
  `[Bug/Problem]`, or `[Neutral]`.
- Click `Who` to show online users.
- Click `Summary` and `Keywords` after several messages.
- Set chatbot personality.
- Ask the chatbot a question and show context-aware response.
- Send `@bot explain this project` in the normal chat input to show chatbot
  group interaction.
- Click `Disconnect` or type `/quit` to show a clean client exit.
- Show one meaningful pi-mono usage, such as:
  - generating the first Tkinter GUI structure,
  - debugging the receive thread,
  - explaining the JSON message protocol,
  - helping write this documentation.

## 3. Discussion

- Libraries used:
  - `socket` for network communication
  - `threading` for simultaneous clients and background receive loop
  - `tkinter` for GUI
  - `json` for structured message protocol
  - `collections.Counter` and `deque` for chat history analysis
- Design decisions:
  - JSON-line messages are easier to parse than plain text messages.
  - Server stores recent chat history for `/summary` and `/keywords`.
  - GUI updates are handled on the Tkinter main thread using a queue.
  - Chatbot runs on the server side so it can join the public group chat.
  - The chatbot calls DeepSeek when `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`,
    and `DEEPSEEK_MODEL` are configured.
  - Sentiment analysis uses the same DeepSeek API and asks the model to
    return one fixed emotion label.

## 4. Analysis and Reflection

- Code organization:
  - protocol code is separated from server and client
  - chatbot logic is separated from GUI
  - server focuses on communication and history commands
- Challenges:
  - keeping the GUI responsive while receiving socket data
  - showing both sent and received messages clearly
  - avoiding duplicated message display
  - keeping chatbot demo working even without an API key
- Possible improvements:
  - add password authentication
  - add file transfer
  - store chat history in a database
  - chatbot can participate in group chat when mentioned with `@bot`
  - replace simple sentiment rules with a stronger NLP model
  - improve bot routing so only one client answers when multiple clients mention `@bot`

## 5. Presentation Quality Tips

- Keep the demo short and direct.
- Use large enough font or zoom for the recorded screen.
- Explain what each button does while clicking it.
- Show the code structure briefly, but spend most time on the working application.
