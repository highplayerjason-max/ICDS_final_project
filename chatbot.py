import os
import random
import urllib.error
import urllib.request
import urllib.parse
import json
import threading

# Optional imports
try:
    from io import BytesIO
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class SimpleContextBot:
    def __init__(self, personality="friendly teaching assistant", max_history=20):
        self.personality = personality
        self.max_history = max_history
        self.history = []
        self.last_status = "local"

    def set_personality(self, personality):
        self.personality = personality.strip() or "friendly teaching assistant"

    def chat(self, user_message):
        self._append_history("user", user_message)
        reply = self._local_reply(user_message)
        self.last_status = "local"
        self._append_history("assistant", reply)
        return reply

    def _append_history(self, role, content):
        self.history.append((role, content))
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def _local_reply(self, user_message):
        text = user_message.lower()
        if any(word in text for word in ["hello", "hi", "hey", "你好"]):
            return f"Hi! I am acting as a {self.personality}. What would you like to discuss?"
        if any(word in text for word in ["summary", "summarize", "总结"]):
            recent = [message for role, message in self.history[-6:] if role == "user"]
            return "Here is a short summary: " + "; ".join(recent[-3:])
        if any(word in text for word in ["help", "project", "final"]):
            return "For this project, focus on showing the GUI, socket communication, chatbot context, and one bonus feature clearly in the demo."
        starters = [
            "I understand. Based on our previous messages,",
            "Good point. With that context,",
            "As your selected personality, I would say",
        ]
        return f"{random.choice(starters)} {user_message}"


class OpenAICompatibleBot(SimpleContextBot):
    def __init__(self, personality="friendly teaching assistant", max_history=20):
        super().__init__(personality, max_history=max_history)
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("PI_MONO_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def chat(self, user_message):
        if not self.api_key:
            return super().chat(user_message)
        self._append_history("user", user_message)
        try:
            reply = self._api_reply()
            self.last_status = "api"
        except (
            urllib.error.URLError,
            TimeoutError,
            KeyError,
            ValueError,
            json.JSONDecodeError,
        ):
            reply = super()._local_reply(user_message)
            self.last_status = "fallback"
        self._append_history("assistant", reply)
        return reply

    def _api_reply(self):
        messages = [
            {
                "role": "system",
                "content": f"You are a {self.personality}. Keep replies concise for a chat app demo.",
            }
        ]
        for role, content in self.history[-10:]:
            messages.append({"role": role, "content": content})
        body = json.dumps({"model": self.model, "messages": messages}).encode("utf-8")
        request = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()


def analyze_sentiment(text):
    """Analyze sentiment using keyword method. Returns Positive/Neutral/Negative."""
    positive_words = {
        "good", "great", "excellent", "happy", "love", "like", "thanks", "nice",
        "awesome", "cool", "成功", "开心", "喜欢", "谢谢", "好", "棒",
    }
    negative_words = {
        "bad", "sad", "angry", "hate", "bug", "error", "fail", "failed",
        "problem", "hungry", "tired", "饿", "难过", "生气", "错误", "失败",
    }
    lowered = text.lower()
    score = 0
    for word in positive_words:
        if word in lowered:
            score += 1
    for word in negative_words:
        if word in lowered:
            score -= 1
    if score > 0:
        return "Positive"
    if score < 0:
        return "Negative"
    return "Neutral"


# ========== NLP Features ==========

def extract_keywords(texts, limit=8):
    """Extract top keywords from text list using frequency analysis."""
    from collections import Counter

    stop_words = {
        "the", "and", "you", "are", "for", "with", "that", "this", "have",
        "just", "but", "not", "can", "will", "from", "about", "what", "when",
        "where", "how", "why", "is", "am", "to", "of", "in", "on", "it", "a",
        "an", "i", "me", "my", "we", "our", "your", "了", "的", "是", "我",
        "你", "他", "她", "它", "们", "和", "在", "有",
    }
    counter = Counter()
    for text in texts:
        cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
        for word in cleaned.split():
            if len(word) > 2 and word not in stop_words:
                counter[word] += 1
    return [word for word, _ in counter.most_common(limit)]


def extract_summary(texts, max_sentences=3):
    """Extract a simple summary using frequency-based sentence selection."""
    if not texts:
        return "No text to summarize."

    # Split into sentences
    all_text = " ".join(texts)
    sentences = [s.strip() for s in all_text.replace("!", ".").replace("?", ".").split(".")
                 if s.strip() and len(s.split()) > 2]

    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    # Score sentences by keyword frequency
    from collections import Counter
    word_freq = Counter()
    for sentence in sentences:
        for word in sentence.lower().split():
            if len(word) > 2:
                word_freq[word] += 1

    scored = []
    for i, sentence in enumerate(sentences):
        score = sum(word_freq.get(word.lower(), 0) for word in sentence.split())
        scored.append((score, i, sentence))

    # Select top sentences in original order
    top = sorted(scored, key=lambda x: x[0], reverse=True)[:max_sentences]
    top = sorted(top, key=lambda x: x[1])
    return " ".join(s[2] for s in top)


# ========== AI Image Generation ==========

def generate_image_pollinations(prompt: str, width=512, height=512) -> bytes:
    """
    Generate image using Pollinations.ai API (free, no registration needed).
    Returns image bytes or None if failed.
    """
    if not PIL_AVAILABLE:
        print("PIL not available. Install with: pip install pillow")
        return None

    try:
        # Pollinations.ai uses simple URL format for image generation
        # The seed parameter ensures reproducibility
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        request = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(request, timeout=30) as response:
            image_data = response.read()

        # Verify it's a valid image
        img = Image.open(BytesIO(image_data))
        return image_data
    except Exception as e:
        print(f"Image generation failed: {e}")
        return None


def generate_image_replicate(prompt: str, api_token: str = None) -> str:
    """
    Generate image using Replicate API (requires registration and payment).
    Returns image URL or error message.
    """
    api_token = api_token or os.getenv("REPLICATE_API_TOKEN")

    if not api_token:
        return "Error: REPLICATE_API_TOKEN not set. Register at https://replicate.com/"

    try:
        import replicate
        replicate.api.token = api_token

        # Use Stable Diffusion v1.5 (common model)
        output = replicate.run(
            "stability-ai/stable-diffusion:a9e6cc406d05889b4d1f38ecdf76b8b7104434305aef149099ac0f11e21eaf70",
            input={"prompt": prompt}
        )
        return output[0] if output else "Image generation returned empty result."
    except Exception as e:
        return f"Error: {str(e)}"


# ========== Enhanced Sentiment Analysis ==========

def analyze_sentiment_textblob(text: str) -> dict:
    """
    Enhanced sentiment analysis using TextBlob if available, else fallback.
    Returns dict with sentiment, polarity, subjectivity, and emoji.
    """
    try:
        from textblob import TextBlob
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1
        subjectivity = blob.sentiment.subjectivity  # 0 to 1

        if polarity > 0.1:
            sentiment = "Positive"
            emoji = "😊"
        elif polarity < -0.1:
            sentiment = "Negative"
            emoji = "😡"
        else:
            sentiment = "Neutral"
            emoji = "😐"

        return {
            "sentiment": sentiment,
            "emoji": emoji,
            "polarity": round(polarity, 2),
            "subjectivity": round(subjectivity, 2)
        }
    except ImportError:
        # Fallback to simple analysis
        result = analyze_sentiment(text)
        emoji_map = {"Positive": "😊", "Negative": "😡", "Neutral": "😐"}
        return {
            "sentiment": result,
            "emoji": emoji_map.get(result, "😐"),
            "polarity": 0,
            "subjectivity": 0
        }