# Distributed Chat Final Project

This project is a socket-based distributed chat system with a Tkinter GUI client.
It includes the compulsory GUI topic, a chatbot selective topic, and several small
bonus features.

**👉 [快速开始指南](QUICK_START.md) | [完整文档](#quick-links)**

## Features

### Core Features
- Socket server with multiple clients
- WeChat-style Tkinter GUI client
- Real-time send and receive display
- Login username
- Online friend list and direct messages
- Public group chat
- Interactive multiplayer Tic-Tac-Toe game
- Emoji buttons
- Server-side group chatbot with context and editable personality

### Advanced Features (Final Project)

**Topic 1: AI Image Generation**
- Generate images using Pollinations.ai (free, no registration)
- Support for Replicate API (high-quality, requires API token)
- `/image <prompt>` command to generate images
- Display generated images in GUI

**Topic 2: NLP Text Analysis**
- Keyword extraction from chat history
- Text summarization with frequency-based algorithm
- Advanced NLP summarization with sentence scoring
- `/keywords` and `/summary_nlp` commands
- Support for optional YAKE and Sumy libraries

**Topic 3: Enhanced Sentiment Analysis**
- Automatic sentiment tagging for all messages [Positive/Neutral/Negative]
- Detailed sentiment analysis with polarity scores
- Emoji indicators (😊 😐 😡)
- Support for TextBlob library for better accuracy
- Support for both English and Chinese text

The chatbot can use an OpenAI-compatible API when environment variables are set.
If no API key is available, it falls back to a local rule-based bot so the demo
still works.

## Files

- `server.py`: multi-client socket chat server with command handling
- `gui_client.py`: Tkinter GUI chat client with advanced features
- `protocol.py`: JSON-line message encoding and decoding
- `chatbot.py`: chatbot, sentiment analysis, NLP, and image generation
- `system_structure.md`: system structure and robustness explanation
- `presentation_outline.md`: suggested video and slide structure
- `FEATURES_GUIDE.md`: detailed guide for all advanced features
- `requirements.txt`: Python package dependencies

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
4. Send messages with automatic sentiment tagging.
5. Test commands and features:
   - Click `Who`, `Summary`, `Summary NLP`, `Keywords` for analysis
   - Click `Generate Image` to create AI images
   - Click `Analyze Sentiment` for detailed sentiment analysis
   - Click `Invite Bot`, `Bot Personality`, `Ask Bot`, and `Game` for other features

## Installation

### Basic Setup (Pollinations.ai - Free)
```powershell
pip install Pillow
python server.py
python gui_client.py
```

### Full Setup (All Features)
```powershell
# Install all dependencies
pip install Pillow textblob yake sumy nltk replicate

# Download NLTK data
python -m nltk.downloader punkt brown

# Run the application
python server.py
python gui_client.py
```

For detailed feature usage, see [FEATURES_GUIDE.md](FEATURES_GUIDE.md).

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

## Quick Links <a name="quick-links"></a>

- 🚀 [快速开始](QUICK_START.md) - 30 秒启动
- 📚 [功能指南](FEATURES_GUIDE.md) - 详细的功能说明
- 🔍 [快速参考](QUICK_REFERENCE.md) - 命令快速查询
- 💡 [使用示例](USAGE_EXAMPLES.md) - 真实场景示例
- ⚙️ [部署和测试](DEPLOYMENT_AND_TESTING.md) - 测试清单
- 📋 [项目总结](PROJECT_COMPLETION_REPORT.md) - 完成报告
- 🔧 [实现细节](IMPLEMENTATION_SUMMARY.md) - 技术细节

## New Advanced Features

See [QUICK_START.md](QUICK_START.md) for a 30-second introduction to:
1. **AI Image Generation** - Generate images with simple text prompts
2. **NLP Text Analysis** - Extract keywords and create summaries
3. **Sentiment Analysis** - Automatic emotion detection with emojis

All features work out-of-the-box with no API keys needed!
