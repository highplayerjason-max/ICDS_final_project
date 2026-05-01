import json
import os
import random
import subprocess
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


# ========== Helper Functions ==========

def get_env(key, default=""):
    """Get environment variable with optional default value."""
    return os.getenv(key, default)


# ========== Constants ==========

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


class OpenAICompatibleBot(SimpleContextBot):
    def __init__(self, personality="friendly teaching assistant", max_history=20):
        super().__init__(personality, max_history=max_history)
        self.provider = (get_env("AI_PROVIDER", "") or "").strip().lower()
        self.api_key = (
            get_env("AI_API_KEY")
            or get_env("DEEPSEEK_API_KEY")
            or get_env("OPENAI_API_KEY")
            or get_env("PI_MONO_API_KEY")
        )
        deepseek_key = get_env("DEEPSEEK_API_KEY")
        ai_base_url = get_env("AI_BASE_URL")
        openai_base_url = get_env("OPENAI_BASE_URL")
        if deepseek_key and not ai_base_url and not openai_base_url:
            self.provider = self.provider or "deepseek"
            self.base_url = "https://api.deepseek.com"
            self.model = get_env("AI_MODEL") or get_env("DEEPSEEK_MODEL", "deepseek-chat")
        else:
            self.provider = self.provider or "openai-compatible"
            self.base_url = ai_base_url or openai_base_url or "https://api.openai.com/v1"
            self.model = get_env("AI_MODEL") or get_env("OPENAI_MODEL", "gpt-4o-mini")

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
            if "unknown url type: https" not in str(exc):
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
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def _curl_chat_completion(self, body):
        result = subprocess.run(
            [
                "curl.exe",
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


_sentiment_bot = OpenAICompatibleBot("sentiment classifier")


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
