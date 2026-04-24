import socket
import threading
from collections import Counter, deque

from protocol import decode_messages, encode_message


HOST = "127.0.0.1"
PORT = 5000


class ChatServer:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.clients = {}
        self.clients_lock = threading.Lock()
        self.history = deque(maxlen=100)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        print(f"Chat server listening on {self.host}:{self.port}")
        while True:
            client_socket, address = self.server_socket.accept()
            threading.Thread(
                target=self.handle_client,
                args=(client_socket, address),
                daemon=True,
            ).start()

    def handle_client(self, client_socket, address):
        username = None
        buffer = b""
        try:
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                buffer += data
                messages, buffer = decode_messages(buffer)
                for message in messages:
                    if message["type"] == "login":
                        username = self.register_client(client_socket, message["sender"], address)
                    elif message["type"] == "chat":
                        self.handle_chat(username, message["content"])
                    elif message["type"] == "command":
                        self.handle_command(client_socket, username, message["content"])
        except (ConnectionError, OSError, ValueError):
            pass
        finally:
            self.remove_client(client_socket, username)

    def register_client(self, client_socket, requested_name, address):
        base_name = requested_name.strip() or f"Guest-{address[1]}"
        username = base_name
        with self.clients_lock:
            existing = set(self.clients.values())
            suffix = 2
            while username in existing:
                username = f"{base_name}{suffix}"
                suffix += 1
            self.clients[client_socket] = username
        self.send_to(client_socket, "system", "Server", f"Welcome, {username}!")
        self.broadcast("system", "Server", f"{username} joined the chat.", exclude=None)
        return username

    def handle_chat(self, username, content):
        if not username:
            return
        text = content.strip()
        if not text:
            return
        self.history.append((username, text))
        self.broadcast("chat", username, text)

    def handle_command(self, client_socket, username, command):
        command = command.strip().lower()
        if command == "/who":
            with self.clients_lock:
                names = sorted(self.clients.values())
            self.send_to(client_socket, "system", "Server", "Online: " + ", ".join(names))
        elif command == "/summary":
            self.send_to(client_socket, "system", "Summary", self.make_summary())
        elif command == "/keywords":
            self.send_to(client_socket, "system", "Keywords", self.make_keywords())
        elif command == "/help":
            self.send_to(client_socket, "system", "Server", "Commands: /who, /summary, /keywords")
        else:
            self.send_to(client_socket, "system", "Server", f"Unknown command: {command}")

    def make_summary(self):
        recent = list(self.history)[-8:]
        if not recent:
            return "No chat history yet."
        speakers = sorted({name for name, _ in recent})
        topics = self.extract_keywords([text for _, text in recent], limit=5)
        return f"Recent chat has {len(recent)} messages from {', '.join(speakers)}. Main topics: {', '.join(topics) or 'none'}."

    def make_keywords(self):
        words = self.extract_keywords([text for _, text in self.history], limit=8)
        return ", ".join(words) if words else "No keywords yet."

    def extract_keywords(self, texts, limit=8):
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

    def broadcast(self, message_type, sender, content, exclude=None):
        packet = encode_message(message_type, sender, content)
        with self.clients_lock:
            sockets = list(self.clients.keys())
        for client_socket in sockets:
            if client_socket is exclude:
                continue
            try:
                client_socket.sendall(packet)
            except OSError:
                self.remove_client(client_socket, self.clients.get(client_socket))

    def send_to(self, client_socket, message_type, sender, content):
        try:
            client_socket.sendall(encode_message(message_type, sender, content))
        except OSError:
            self.remove_client(client_socket, self.clients.get(client_socket))

    def remove_client(self, client_socket, username):
        removed = False
        with self.clients_lock:
            if client_socket in self.clients:
                removed = True
                username = self.clients.pop(client_socket)
        try:
            client_socket.close()
        except OSError:
            pass
        if removed and username:
            self.broadcast("system", "Server", f"{username} left the chat.")


if __name__ == "__main__":
    ChatServer().start()
