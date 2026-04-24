import queue
import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog

from chatbot import OpenAICompatibleBot, analyze_sentiment
from protocol import decode_messages, encode_message


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000


class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Distributed Chat GUI")
        self.root.geometry("760x560")
        self.socket = None
        self.username = ""
        self.incoming = queue.Queue()
        self.connected = False
        self.bot = OpenAICompatibleBot()

        self.build_login()
        self.build_chat()
        self.root.after(100, self.process_incoming)

    def build_login(self):
        frame = tk.Frame(self.root, padx=10, pady=8)
        frame.pack(fill=tk.X)

        tk.Label(frame, text="Host").grid(row=0, column=0, sticky="w")
        self.host_entry = tk.Entry(frame, width=14)
        self.host_entry.insert(0, DEFAULT_HOST)
        self.host_entry.grid(row=0, column=1, padx=4)

        tk.Label(frame, text="Port").grid(row=0, column=2, sticky="w")
        self.port_entry = tk.Entry(frame, width=6)
        self.port_entry.insert(0, str(DEFAULT_PORT))
        self.port_entry.grid(row=0, column=3, padx=4)

        tk.Label(frame, text="Name").grid(row=0, column=4, sticky="w")
        self.name_entry = tk.Entry(frame, width=16)
        self.name_entry.insert(0, "Student")
        self.name_entry.grid(row=0, column=5, padx=4)

        self.connect_button = tk.Button(frame, text="Connect", command=self.connect)
        self.connect_button.grid(row=0, column=6, padx=4)

        self.status_label = tk.Label(frame, text="Disconnected", fg="red")
        self.status_label.grid(row=0, column=7, padx=8)

    def build_chat(self):
        main = tk.Frame(self.root, padx=10, pady=6)
        main.pack(fill=tk.BOTH, expand=True)

        self.chat_area = scrolledtext.ScrolledText(main, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        self.chat_area.tag_config("system", foreground="#666666")
        self.chat_area.tag_config("me", foreground="#0b63ce")
        self.chat_area.tag_config("other", foreground="#111111")
        self.chat_area.tag_config("bot", foreground="#7a1fa2")

        tools = tk.Frame(main, pady=6)
        tools.pack(fill=tk.X)
        tk.Button(tools, text="Who", command=lambda: self.send_command("/who")).pack(side=tk.LEFT, padx=2)
        tk.Button(tools, text="Summary", command=lambda: self.send_command("/summary")).pack(side=tk.LEFT, padx=2)
        tk.Button(tools, text="Keywords", command=lambda: self.send_command("/keywords")).pack(side=tk.LEFT, padx=2)
        tk.Button(tools, text="Bot Personality", command=self.set_bot_personality).pack(side=tk.LEFT, padx=2)
        tk.Button(tools, text="Ask Bot", command=self.ask_bot).pack(side=tk.LEFT, padx=2)
        for emoji in ["😊", "😂", "👍", "❤️"]:
            tk.Button(tools, text=emoji, width=3, command=lambda e=emoji: self.insert_emoji(e)).pack(side=tk.RIGHT, padx=2)

        input_frame = tk.Frame(main)
        input_frame.pack(fill=tk.X)
        self.message_entry = tk.Entry(input_frame)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.message_entry.bind("<Return>", lambda event: self.send_message())
        tk.Button(input_frame, text="Send", command=self.send_message).pack(side=tk.LEFT, padx=5)

    def connect(self):
        if self.connected:
            return
        host = self.host_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Invalid port", "Port must be a number.")
            return
        self.username = self.name_entry.get().strip() or "Student"
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.socket.sendall(encode_message("login", self.username, ""))
        except OSError as exc:
            messagebox.showerror("Connection failed", str(exc))
            return
        self.connected = True
        self.status_label.config(text="Connected", fg="green")
        self.connect_button.config(state=tk.DISABLED)
        threading.Thread(target=self.receive_loop, daemon=True).start()

    def receive_loop(self):
        buffer = b""
        while self.connected:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                buffer += data
                messages, buffer = decode_messages(buffer)
                for message in messages:
                    self.incoming.put(message)
            except (OSError, ValueError):
                break
        self.connected = False
        self.incoming.put({"type": "system", "sender": "Client", "content": "Disconnected from server."})

    def process_incoming(self):
        while True:
            try:
                message = self.incoming.get_nowait()
            except queue.Empty:
                break
            sender = message.get("sender", "Unknown")
            content = message.get("content", "")
            if message.get("type") == "system":
                self.display_message(sender, content, "system")
            elif sender == self.username:
                self.display_message("Me", content, "me")
            else:
                self.display_message(sender, content, "other")
        self.root.after(100, self.process_incoming)

    def display_message(self, sender, content, tag):
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, f"{sender}: {content}\n", tag)
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def send_message(self):
        text = self.message_entry.get().strip()
        if not text:
            return
        self.message_entry.delete(0, tk.END)
        if text.startswith("/"):
            self.send_command(text)
            return
        if not self.ensure_connected():
            return
        sentiment = analyze_sentiment(text)
        content = f"{text} [{sentiment}]"
        try:
            self.socket.sendall(encode_message("chat", self.username, content))
        except OSError:
            self.display_message("Client", "Message failed to send.", "system")

    def send_command(self, command):
        if not self.ensure_connected():
            return
        try:
            self.socket.sendall(encode_message("command", self.username, command))
        except OSError:
            self.display_message("Client", "Command failed to send.", "system")

    def ensure_connected(self):
        if self.connected:
            return True
        messagebox.showwarning("Not connected", "Start server.py first, then connect.")
        return False

    def insert_emoji(self, emoji):
        self.message_entry.insert(tk.INSERT, emoji)
        self.message_entry.focus_set()

    def set_bot_personality(self):
        value = simpledialog.askstring(
            "Bot Personality",
            "Enter a personality, for example: funny assistant, strict teacher, project mentor",
            initialvalue=self.bot.personality,
        )
        if value is not None:
            self.bot.set_personality(value)
            self.display_message("Bot", f"Personality set to: {self.bot.personality}", "bot")

    def ask_bot(self):
        prompt = self.message_entry.get().strip()
        if not prompt:
            prompt = simpledialog.askstring("Ask Bot", "Message to chatbot:")
        if not prompt:
            return
        self.display_message("Me -> Bot", prompt, "me")
        self.message_entry.delete(0, tk.END)
        threading.Thread(target=self.get_bot_reply, args=(prompt,), daemon=True).start()

    def get_bot_reply(self, prompt):
        reply = self.bot.chat(prompt)
        if self.bot.last_error:
            reply = f"{reply}\n(API fallback: {self.bot.last_error})"
        self.incoming.put({"type": "system", "sender": "Bot", "content": reply})

    def close(self):
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except OSError:
                pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()
