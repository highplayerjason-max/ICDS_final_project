import os
import random
import urllib.error
import urllib.request
import json


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
