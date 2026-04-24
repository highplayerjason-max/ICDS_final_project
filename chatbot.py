import os
import random
import urllib.error
import urllib.request
import json


class SimpleContextBot:
    def __init__(self, personality="friendly teaching assistant"):
        self.personality = personality
        self.history = []
        self.last_error = ""

    def set_personality(self, personality):
        self.personality = personality.strip() or "friendly teaching assistant"

    def chat(self, user_message):
        self.history.append(("user", user_message))
        reply = self._local_reply(user_message)
        self.history.append(("assistant", reply))
        return reply

    def _local_reply(self, user_message):
        text = user_message.lower()
        if self._contains_abuse(text):
            return "Please keep the chat respectful. I can still help with the project, debugging, or presentation script."
        if any(word in text for word in ["hello", "hi", "hey", "你好"]):
            return f"Hi! I am acting as a {self.personality}. What would you like to discuss?"
        if any(word in text for word in ["summary", "summarize", "总结"]):
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
        blocked_words = {
            "nigga", "nigger", "faggot", "retard",
        }
        return any(word in text for word in blocked_words)


class OpenAICompatibleBot(SimpleContextBot):
    def __init__(self, personality="friendly teaching assistant"):
        super().__init__(personality)
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("PI_MONO_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def chat(self, user_message):
        if not self.api_key:
            self.last_error = "OPENAI_API_KEY is not configured for this process."
            return super().chat(user_message)
        self.history.append(("user", user_message))
        try:
            reply = self._api_reply()
            self.last_error = ""
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            reply = super()._local_reply(user_message)
        self.history.append(("assistant", reply))
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
    categories = {
        "Excited": {
            "awesome", "amazing", "excellent", "great", "cool", "wow",
            "excited", "perfect", "fantastic", "棒", "太好了", "牛", "激动",
        },
        "Happy": {
            "happy", "glad", "love", "like", "thanks", "thank", "nice",
            "开心", "喜欢", "谢谢", "爱", "满意",
        },
        "Confused": {
            "confused", "unclear", "why", "how", "what", "stuck", "question",
            "不懂", "不会", "为什么", "怎么", "疑惑", "卡住",
        },
        "Worried": {
            "worried", "nervous", "afraid", "scared", "deadline", "urgent",
            "担心", "紧张", "害怕", "来不及", "急",
        },
        "Sad": {
            "sad", "upset", "tired", "hungry", "lonely", "disappointed",
            "难过", "累", "饿", "失望", "不开心",
        },
        "Angry": {
            "angry", "mad", "hate", "annoying", "terrible", "awful",
            "生气", "烦", "讨厌", "糟糕", "离谱",
        },
        "Bug/Problem": {
            "bug", "error", "fail", "failed", "problem", "crash", "broken",
            "错误", "失败", "报错", "崩溃", "问题", "坏了",
        },
    }
    lowered = text.lower()
    scores = {}
    for category, words in categories.items():
        scores[category] = sum(1 for word in words if word in lowered)

    best_category = max(scores, key=scores.get)
    if scores[best_category] == 0:
        return "Neutral"
    return best_category
