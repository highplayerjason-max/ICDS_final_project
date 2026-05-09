import json
import os
import random
import subprocess
import ssl
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request

try:
    import certifi
except ImportError:
    certifi = None

# Optional imports
try:
    from io import BytesIO
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ========== Helper Functions ==========

def get_env(key, default=""):
    """Get environment variable with optional default value."""
    return os.getenv(key, default)


# ========== Constants ==========

# Optional repo-local DeepSeek defaults.
# Keep BOTH bot API configs together here:
# - GROUP bot (server-side @bot)
# - LOCAL bot (GUI Local Bot button)
DEFAULT_DEEPSEEK_API_KEY_GROUP = "sk-4d8c9df2732843e4942159d5713eee4d"
DEFAULT_DEEPSEEK_BASE_URL_GROUP = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL_GROUP = "deepseek-chat"

DEFAULT_DEEPSEEK_API_KEY_LOCAL = "sk-4d8c9df2732843e4942159d5713eee4d"
DEFAULT_DEEPSEEK_BASE_URL_LOCAL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL_LOCAL = "deepseek-chat"

SENTIMENT_LABELS = [
    "Excited", "Happy", "Confused", "Worried", "Sad", "Angry", "Bug/Problem", "Neutral"
]


class SimpleContextBot:
    def __init__(self, personality="friendly teaching assistant", max_history=20):
        self.personality = personality
        self.max_history = max_history
        self.history = []
        self.last_error = ""
        self.last_status = "local"

    def set_personality(self, personality):
        self.personality = personality.strip() or "friendly teaching assistant"

    def chat(self, user_message):
        self._append_history("user", user_message)
        reply = self._local_reply(user_message)
        self.last_error = ""
        self.last_status = "local"
        self._append_history("assistant", reply)
        return reply

    def _append_history(self, role, content):
        self.history.append((role, content))
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def _local_reply(self, user_message):
        text = user_message.lower()
        if self._contains_abuse(text):
            return "Please keep the chat respectful. I can still help with the project, debugging, or presentation script."
        if any(word in text for word in ["hello", "hi", "hey"]):
            return f"Hi! I am acting as a {self.personality}. What would you like to discuss?"
        if any(word in text for word in ["summary", "summarize"]):
            recent = [message for role, message in self.history[-6:] if role == "user"]
            return "Here is a short summary: " + "; ".join(recent[-3:])
        if any(word in text for word in ["help", "project", "final"]):
            return "For this project, focus on showing the GUI, socket communication, chatbot context, and one bonus feature clearly in the demo."
        starters = [
            "I can help with that. Please give me one specific goal or question.",
            "For the final project, I can help explain code, debug errors, or write demo text.",
            "Please ask a project-related question, and I will answer directly.",
        ]
        return random.choice(starters)

    def _contains_abuse(self, text):
        blocked_words = {"nigga", "nigger", "faggot", "retard"}
        return any(word in text for word in blocked_words)


class DeepSeekBot(SimpleContextBot):
    def __init__(self, personality="friendly teaching assistant", max_history=20, api_profile="group"):
        super().__init__(personality, max_history=max_history)
        profile = (api_profile or "group").strip().lower()
        if profile == "local":
            repo_deepseek_key = DEFAULT_DEEPSEEK_API_KEY_LOCAL.strip()
            default_base_url = DEFAULT_DEEPSEEK_BASE_URL_LOCAL
            default_model = DEFAULT_DEEPSEEK_MODEL_LOCAL
            env_key = get_env("DEEPSEEK_API_KEY_LOCAL")
            env_base_url = get_env("DEEPSEEK_BASE_URL_LOCAL")
            env_model = get_env("DEEPSEEK_MODEL_LOCAL")
        else:
            repo_deepseek_key = DEFAULT_DEEPSEEK_API_KEY_GROUP.strip()
            default_base_url = DEFAULT_DEEPSEEK_BASE_URL_GROUP
            default_model = DEFAULT_DEEPSEEK_MODEL_GROUP
            env_key = get_env("DEEPSEEK_API_KEY_GROUP")
            env_base_url = get_env("DEEPSEEK_BASE_URL_GROUP")
            env_model = get_env("DEEPSEEK_MODEL_GROUP")

        self.provider = "deepseek"
        self.api_key = env_key or get_env("DEEPSEEK_API_KEY") or repo_deepseek_key
        self.base_url = env_base_url or get_env("DEEPSEEK_BASE_URL") or default_base_url
        self.model = env_model or get_env("DEEPSEEK_MODEL") or default_model

    def chat(self, user_message):
        if not self.api_key:
            return super().chat(user_message)
        self._append_history("user", user_message)
        try:
            reply = self._api_reply()
            self.last_error = ""
            self.last_status = "api"
        except (
            urllib.error.URLError,
            TimeoutError,
            KeyError,
            ValueError,
            json.JSONDecodeError,
            subprocess.SubprocessError,
            OSError,
        ) as exc:
            self.last_error = self._format_error(exc)
            reply = super()._local_reply(user_message)
            self.last_status = "fallback"
        self._append_history("assistant", reply)
        return reply

    def classify_sentiment(self, text):
        if not self.api_key:
            self.last_error = ""
            self.last_status = "local"
            return classify_sentiment_locally(text)

        messages = [
            {
                "role": "system",
                "content": (
                    "Classify the user's message into exactly one sentiment label. "
                    "Allowed labels: Excited, Happy, Confused, Worried, Sad, Angry, "
                    "Bug/Problem, Neutral. Reply with only the label."
                ),
            },
            {"role": "user", "content": text},
        ]
        try:
            reply = self._chat_completion(messages).strip()
            self.last_error = ""
            self.last_status = "api"
        except (
            urllib.error.URLError,
            TimeoutError,
            KeyError,
            ValueError,
            json.JSONDecodeError,
            subprocess.SubprocessError,
            OSError,
        ) as exc:
            self.last_error = self._format_error(exc)
            self.last_status = "fallback"
            return classify_sentiment_locally(text)

        for label in SENTIMENT_LABELS:
            if label.lower() == reply.lower():
                return label
        for label in SENTIMENT_LABELS:
            if label.lower() in reply.lower():
                return label
        return "Neutral"

    def _api_reply(self):
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a {self.personality}. Keep replies concise for a chat app demo. "
                    "Reply in English unless the user asks for Chinese. Use plain ASCII punctuation."
                ),
            }
        ]
        for role, content in self.history[-10:]:
            messages.append({"role": role, "content": content})
        return self._chat_completion(messages)

    def _chat_completion(self, messages):
        body = json.dumps({"model": self.model, "messages": messages}, ensure_ascii=True)
        try:
            data = self._urllib_chat_completion(body.encode("utf-8"))
        except urllib.error.URLError as exc:
            if "unknown url type: https" not in str(exc) and not _is_ssl_related_error(exc):
                raise
            data = self._curl_chat_completion(body)
        return data["choices"][0]["message"]["content"].strip()

    def _urllib_chat_completion(self, body):
        request = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json; charset=utf-8",
            },
        )

        def _fetch_with_context(ctx):
            opener = _build_https_opener(ctx)
            with opener.open(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))

        try:
            ctx = _ssl_context_for_outbound_https()
            return _fetch_with_context(ctx)
        except Exception as first:
            if sys.platform == "win32" and certifi and _is_ssl_related_error(first):
                try:
                    alt = ssl.create_default_context()
                    alt.load_verify_locations(cafile=certifi.where())
                    return _fetch_with_context(alt)
                except Exception as second:
                    raise RuntimeError(
                        f"SSL failed (Windows): first try {type(first).__name__}: {first!s}; "
                        f"certifi retry {type(second).__name__}: {second!s}"
                    ) from second
            raise

    def _curl_chat_completion(self, body):
        curl_bin = "curl.exe" if sys.platform == "win32" else "curl"
        result = subprocess.run(
            [
                curl_bin,
                "--silent",
                "--show-error",
                "--fail",
                "--request",
                "POST",
                "--url",
                f'{self.base_url.rstrip("/")}/chat/completions',
                "--header",
                f"Authorization: Bearer {self.api_key}",
                "--header",
                "Content-Type: application/json; charset=utf-8",
                "--data-binary",
                "@-",
            ],
            input=body.encode("utf-8"),
            capture_output=True,
            timeout=60,
            check=True,
        )
        return json.loads(result.stdout.decode("utf-8"))

    def _format_error(self, exc):
        if isinstance(exc, subprocess.CalledProcessError):
            stderr = self._decode_process_output(exc.stderr).strip()
            if stderr:
                return f"curl exited with code {exc.returncode}: {stderr}"
            return f"curl exited with code {exc.returncode}"
        return f"{type(exc).__name__}: {exc}"

    def _decode_process_output(self, value):
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value or ""


_local_bot_sessions = {}


def get_local_bot_session(session_id="default", personality="friendly teaching assistant", max_history=20):
    """
    Return a local chatbot session scoped by session_id.

    This session is "local" in scope (isolated per GUI/session), but it uses
    DeepSeekBot internally so it can call the AI model API.
    """
    key = (session_id or "default").strip() or "default"
    if key not in _local_bot_sessions:
        _local_bot_sessions[key] = DeepSeekBot(
            personality=personality,
            max_history=max_history,
            api_profile="local",
        )
    bot = _local_bot_sessions[key]
    bot.set_personality(personality)
    return bot


def chat_local_only(user_message, session_id="default", personality="friendly teaching assistant", max_history=20):
    """
    Chat with a local-scoped bot session and return the reply string.

    - Uses DeepSeek API when available.
    - Falls back to local rule-based reply if API is unavailable.
    """
    bot = get_local_bot_session(
        session_id=session_id,
        personality=personality,
        max_history=max_history,
    )
    reply = bot.chat(user_message)
    if bot.last_status == "fallback":
        return f"{reply} (API unavailable, local fallback used.)"
    return reply


def reset_local_bot_session(session_id="default"):
    """
    Reset one local-only session. Returns True if a session was removed.
    """
    key = (session_id or "default").strip() or "default"
    return _local_bot_sessions.pop(key, None) is not None


def create_chatbot(local_only=False, personality="friendly teaching assistant", max_history=20):
    """
    Factory function for chatbot creation.

    local_only controls conversation scope only. Both modes use DeepSeekBot
    behavior (API first, local fallback) to keep API compatibility.
    """
    return DeepSeekBot(personality=personality, max_history=max_history)


def classify_sentiment_locally(text):
    categories = {
        "Excited": {
            "awesome", "amazing", "excellent", "great", "cool", "wow",
            "excited", "perfect", "fantastic",
        },
        "Happy": {
            "happy", "glad", "love", "like", "thanks", "thank", "nice",
        },
        "Confused": {
            "confused", "unclear", "why", "how", "what", "stuck", "question",
        },
        "Worried": {
            "worried", "nervous", "afraid", "scared", "deadline", "urgent",
        },
        "Sad": {
            "sad", "upset", "tired", "hungry", "lonely", "disappointed",
        },
        "Angry": {
            "angry", "mad", "hate", "annoying", "terrible", "awful",
        },
        "Bug/Problem": {
            "bug", "error", "fail", "failed", "problem", "crash", "broken",
        },
    }
    lowered = text.lower()
    scores = {
        category: sum(1 for word in words if word in lowered)
        for category, words in categories.items()
    }
    best_category = max(scores, key=scores.get)
    if scores[best_category] == 0:
        return "Neutral"
    return best_category


_sentiment_bot = DeepSeekBot("sentiment classifier")


def analyze_sentiment(text):
    """Analyze sentiment with DeepSeek first, then local keyword fallback."""
    return _sentiment_bot.classify_sentiment(text)


def analyze_sentiment_locally(text):
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


def _ssl_context_for_outbound_https():
    """
    TLS for HTTPS image fetch. On Windows, use default context (SCHANNEL / OS trust
    store) so corporate proxy CA roots work; do not force certifi-only, which often
    breaks SSL behind enterprise MITM proxies.
    """
    ctx = ssl.create_default_context()
    if sys.platform == "win32":
        return ctx
    if certifi:
        try:
            ctx.load_verify_locations(cafile=certifi.where())
        except (ssl.SSLError, OSError):
            pass
    return ctx


def _build_https_opener(ssl_context):
    """Respect HTTP(S)_PROXY and Windows system proxy via getproxies()."""
    handlers = [urllib.request.HTTPSHandler(context=ssl_context)]
    proxies = urllib.request.getproxies()
    if proxies:
        handlers.insert(0, urllib.request.ProxyHandler(proxies))
    return urllib.request.build_opener(*handlers)


def _is_ssl_related_error(exc: BaseException) -> bool:
    if isinstance(exc, ssl.SSLError):
        return True
    if isinstance(exc, urllib.error.URLError) and isinstance(exc.reason, ssl.SSLError):
        return True
    return False


def _looks_like_image_bytes(data: bytes) -> bool:
    if not data or len(data) < 12:
        return False
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if data[:3] == b"\xff\xd8\xff":
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return True
    if data[:4] == b"RIFF" and len(data) > 12 and data[8:12] == b"WEBP":
        return True
    return False


def generate_image_pollinations(prompt: str, width=512, height=512) -> bytes:
    """
    Generate image using Pollinations.ai API (free, no registration needed).
    Returns image bytes or None if failed.
    """
    if not PIL_AVAILABLE:
        print("PIL not available. Install with: pip install pillow")
        return None

    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    request = urllib.request.Request(url, headers=headers)

    def _fetch_with_context(ctx: ssl.SSLContext):
        opener = _build_https_opener(ctx)
        with opener.open(request, timeout=90) as response:
            raw = response.read()
            ctype = response.headers.get("Content-Type", "")
        return raw, ctype

    try:
        ctx = _ssl_context_for_outbound_https()
        image_data, content_type = _fetch_with_context(ctx)
    except Exception as first:
        if sys.platform == "win32" and certifi and _is_ssl_related_error(first):
            try:
                alt = ssl.create_default_context()
                alt.load_verify_locations(cafile=certifi.where())
                image_data, content_type = _fetch_with_context(alt)
            except Exception as second:
                raise RuntimeError(
                    f"SSL failed (Windows): first try {type(first).__name__}: {first!s}; "
                    f"certifi retry {type(second).__name__}: {second!s}"
                ) from second
        else:
            raise RuntimeError(f"{type(first).__name__}: {repr(first)}") from first

    try:
        Image.open(BytesIO(image_data)).verify()
    except Exception as e:
        head = image_data[:200].decode("utf-8", errors="replace").replace("\n", " ")
        hint = ""
        if not _looks_like_image_bytes(image_data):
            hint = (
                "Body does not look like a common image signature (PNG/JPEG/WebP/GIF). "
                "Often a corporate proxy returns an HTML login or block page. "
            )
        raise RuntimeError(
            f"{hint}Content-Type={content_type!r}, preview={head!r}. "
            f"PIL: {type(e).__name__}: {repr(e)}"
        ) from e

    return image_data


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
    Enhanced sentiment analysis using DeepSeek if available, else fallback.
    Returns dict with sentiment, status, and display emoji.
    """
    result = analyze_sentiment(text)
    emoji_map = {
        "Excited": ":D",
        "Happy": ":)",
        "Confused": "?",
        "Worried": ":/",
        "Sad": ":(",
        "Angry": ">:(",
        "Bug/Problem": "!",
        "Neutral": ":|",
        "Positive": ":)",
        "Negative": ":(",
    }
    return {
        "sentiment": result,
        "emoji": emoji_map.get(result, ":|"),
        "polarity": 0,
        "subjectivity": 0,
        "status": _sentiment_bot.last_status,
    }

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
