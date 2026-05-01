import queue
import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog
import base64

# Optional imports
try:
    from io import BytesIO
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from chatbot import analyze_sentiment, analyze_sentiment_textblob
from protocol import ProtocolError, decode_messages, encode_message


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
PUBLIC_ROOM_ID = "public"
PUBLIC_ROOM_NAME = "Public Chat"


class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Distributed Chat")
        self.root.geometry("980x660")
        self.root.minsize(860, 560)
        self.socket = None
        self.username = ""
        self.incoming = queue.Queue()
        self.connected = False
        self.rooms = {PUBLIC_ROOM_ID: PUBLIC_ROOM_NAME}
        self.online_users = []
        self.current_conversation_type = "group"
        self.current_conversation_id = PUBLIC_ROOM_ID
        self.current_target = ""
        self.conversation_titles = {PUBLIC_ROOM_ID: PUBLIC_ROOM_NAME}
        self.conversation_messages = {}
        self.game_window = None
        self.game_buttons = []
        self.game_status = None
        self.game_symbol_label = None
        self.current_game_id = ""
        self.current_game_over = False

        self.build_layout()
        self.root.after(100, self.process_incoming)

    def build_layout(self):
        self.root.configure(bg="#f5f5f5")
        container = tk.Frame(self.root, bg="#f5f5f5")
        container.pack(fill=tk.BOTH, expand=True)

        self.sidebar = tk.Frame(container, width=250, bg="#ededed")
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        self.chat_panel = tk.Frame(container, bg="#f7f7f7")
        self.chat_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.build_sidebar()
        self.build_chat_panel()
        self.select_group(PUBLIC_ROOM_ID)

    def build_sidebar(self):
        connect_frame = tk.Frame(self.sidebar, bg="#ededed", padx=12, pady=12)
        connect_frame.pack(fill=tk.X)

        tk.Label(connect_frame, text="Distributed Chat", bg="#ededed", font=("Arial", 15, "bold")).pack(anchor="w")
        self.status_label = tk.Label(connect_frame, text="Disconnected", fg="#c0392b", bg="#ededed")
        self.status_label.pack(anchor="w", pady=(2, 10))

        tk.Label(connect_frame, text="Host", bg="#ededed").pack(anchor="w")
        self.host_entry = tk.Entry(connect_frame)
        self.host_entry.insert(0, DEFAULT_HOST)
        self.host_entry.pack(fill=tk.X, pady=(0, 6))

        tk.Label(connect_frame, text="Port", bg="#ededed").pack(anchor="w")
        self.port_entry = tk.Entry(connect_frame)
        self.port_entry.insert(0, str(DEFAULT_PORT))
        self.port_entry.pack(fill=tk.X, pady=(0, 6))

        tk.Label(connect_frame, text="Name", bg="#ededed").pack(anchor="w")
        self.name_entry = tk.Entry(connect_frame)
        self.name_entry.insert(0, "Student")
        self.name_entry.pack(fill=tk.X, pady=(0, 8))

        buttons = tk.Frame(connect_frame, bg="#ededed")
        buttons.pack(fill=tk.X)
        self.connect_button = tk.Button(buttons, text="Connect", command=self.connect)
        self.connect_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.disconnect_button = tk.Button(buttons, text="Disconnect", command=self.disconnect, state=tk.DISABLED)
        self.disconnect_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        tk.Label(self.sidebar, text="Group Chats", anchor="w", bg="#ededed", fg="#555555", padx=12).pack(fill=tk.X)
        self.room_list = tk.Listbox(self.sidebar, height=4, bd=0, activestyle="none", exportselection=False)
        self.room_list.pack(fill=tk.X, padx=12, pady=(4, 12))
        self.room_list.bind("<<ListboxSelect>>", self.on_room_selected)

        tk.Label(self.sidebar, text="Online Friends", anchor="w", bg="#ededed", fg="#555555", padx=12).pack(fill=tk.X)
        self.user_list = tk.Listbox(self.sidebar, bd=0, activestyle="none", exportselection=False)
        self.user_list.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 12))
        self.user_list.bind("<<ListboxSelect>>", self.on_user_selected)
        self.refresh_room_list()

    def build_chat_panel(self):
        header = tk.Frame(self.chat_panel, bg="#f7f7f7", padx=18, pady=12)
        header.pack(fill=tk.X)
        self.conversation_label = tk.Label(header, text=PUBLIC_ROOM_NAME, bg="#f7f7f7", font=("Arial", 16, "bold"))
        self.conversation_label.pack(side=tk.LEFT)
        self.conversation_hint = tk.Label(header, text="Group chat", bg="#f7f7f7", fg="#777777")
        self.conversation_hint.pack(side=tk.RIGHT)

        self.chat_area = scrolledtext.ScrolledText(
            self.chat_panel,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#ffffff",
            bd=0,
            padx=14,
            pady=12,
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=14)
        self.chat_area.tag_config("system", foreground="#666666")
        self.chat_area.tag_config("me", foreground="#0b63ce")
        self.chat_area.tag_config("other", foreground="#111111")
        self.chat_area.tag_config("bot", foreground="#7a1fa2")

        composer = tk.Frame(self.chat_panel, bg="#f7f7f7", padx=14, pady=10)
        composer.pack(fill=tk.X)

        tools = tk.Frame(composer, bg="#f7f7f7")
        tools.pack(fill=tk.X, pady=(0, 6))
        tk.Button(tools, text="Who", command=lambda: self.send_command("/who")).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(tools, text="Summary", command=lambda: self.send_command("/summary")).pack(side=tk.LEFT, padx=4)
        tk.Button(tools, text="Keywords", command=lambda: self.send_command("/keywords")).pack(side=tk.LEFT, padx=4)
        tk.Button(tools, text="Summary NLP", command=lambda: self.send_command("/summary_nlp")).pack(side=tk.LEFT, padx=4)
        tk.Button(tools, text="Generate Image", command=self.generate_image_dialog).pack(side=tk.LEFT, padx=4)
        tk.Button(tools, text="Invite Bot", command=lambda: self.send_command("/bot join")).pack(side=tk.LEFT, padx=4)
        for emoji in ["😊", "😂", "👍", "❤️"]:
            tk.Button(tools, text=emoji, width=3, command=lambda e=emoji: self.insert_emoji(e)).pack(side=tk.RIGHT, padx=2)

        tools2 = tk.Frame(composer, bg="#f7f7f7")
        tools2.pack(fill=tk.X, pady=(0, 6))
        tk.Button(tools2, text="Bot Personality", command=self.set_bot_personality).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(tools2, text="Ask Bot", command=self.ask_group_bot).pack(side=tk.LEFT, padx=4)
        tk.Button(tools2, text="Analyze Sentiment", command=self.analyze_sentiment_dialog).pack(side=tk.LEFT, padx=4)
        tk.Button(tools2, text="Game", command=self.open_game_window).pack(side=tk.LEFT, padx=4)

        input_frame = tk.Frame(composer, bg="#f7f7f7")
        input_frame.pack(fill=tk.X)
        self.message_entry = tk.Text(input_frame, height=4, wrap=tk.WORD, bd=1, relief=tk.SOLID)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.message_entry.bind("<Command-Return>", lambda event: self.send_message())
        self.message_entry.bind("<Control-Return>", lambda event: self.send_message())
        tk.Button(input_frame, text="Send", width=10, command=self.send_message).pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0))

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
        self.disconnect_button.config(state=tk.NORMAL)
        threading.Thread(target=self.receive_loop, daemon=True).start()

    def disconnect(self):
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except OSError:
                pass
        self.socket = None
        self.status_label.config(text="Disconnected", fg="#c0392b")
        self.connect_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.DISABLED)

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
        self.incoming.put({"type": "disconnect", "sender": "Client", "content": "Disconnected from server."})

    def process_incoming(self):
        while True:
            try:
                message = self.incoming.get_nowait()
            except queue.Empty:
                break
            sender = message.get("sender", "Unknown")
            content = message.get("content", "")
            message_type = message.get("type")
            if message_type == "login_ack":
                self.username = message.get("metadata", {}).get("username", self.username)
                self.name_entry.delete(0, tk.END)
                self.name_entry.insert(0, self.username)
                self.add_message(PUBLIC_ROOM_ID, sender, content, "system")
            elif message_type == "user_list":
                self.online_users = message.get("metadata", {}).get("users", [])
                self.refresh_user_list()
            elif message_type == "room_list":
                rooms = message.get("metadata", {}).get("rooms", [])
                self.rooms = {room["id"]: room["name"] for room in rooms} or {PUBLIC_ROOM_ID: PUBLIC_ROOM_NAME}
                self.refresh_room_list()
            elif message_type == "system":
                conversation_id = message.get("conversation_id") or self.current_conversation_id
                self.add_message(conversation_id, sender, content, "system")
            elif message_type == "chat":
                conversation_id = self.resolve_message_conversation(message)
                tag = "bot" if sender == "Bot" else "me" if sender == self.username else "other"
                display_sender = "Me" if sender == self.username else sender
                self.add_message(conversation_id, display_sender, content, tag)
            elif message_type == "image":
                conversation_id = message.get("conversation_id") or self.current_conversation_id
                self.handle_image_message(message)
                content = f"[Image: {message.get('metadata', {}).get('prompt', 'Generated Image')}]"
                self.add_message(conversation_id, sender, content, "system")
            elif message_type == "disconnect":
                self.disconnect()
                self.add_message(self.current_conversation_id, sender, content, "system")
            elif message_type in {"game_waiting", "game_start", "game_state", "game_over", "game_error"}:
                self.handle_game_message(message)
            else:
                self.add_message(self.current_conversation_id, sender, content, "system")
        self.root.after(100, self.process_incoming)

    def add_message(self, conversation_id, sender, content, tag):
        self.conversation_messages.setdefault(conversation_id, []).append((sender, content, tag))
        if conversation_id == self.current_conversation_id:
            self.display_message(sender, content, tag)

    def display_message(self, sender, content, tag):
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, f"{sender}: {content}\n", tag)
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def send_message(self):
        text = self.message_entry.get("1.0", tk.END).strip()
        if not text:
            return
        if text.startswith("/"):
            self.send_command(text)
            self.message_entry.delete("1.0", tk.END)
            return
        if not self.ensure_connected():
            return
        self.message_entry.delete("1.0", tk.END)
        sentiment = analyze_sentiment(text)
        content = f"{text} [{sentiment}]"
        try:
            self.socket.sendall(
                encode_message(
                    "chat",
                    self.username,
                    content,
                    conversation_type=self.current_conversation_type,
                    conversation_id=self.current_conversation_id,
                    target=self.current_target,
                )
            )
        except (OSError, ProtocolError):
            self.display_message("Client", "Message failed to send.", "system")

    def send_command(self, command):
        if not self.ensure_connected():
            return
        try:
            self.socket.sendall(
                encode_message(
                    "command",
                    self.username,
                    command,
                    conversation_type=self.current_conversation_type,
                    conversation_id=self.current_conversation_id,
                    target=self.current_target,
                )
            )
        except (OSError, ProtocolError):
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
            initialvalue="friendly group chat assistant",
        )
        if value is not None:
            self.send_command(f"/bot personality {value}")

    def ask_group_bot(self):
        if self.current_conversation_type != "group":
            messagebox.showinfo("Group bot", "Select a group chat before asking the group bot.")
            return
        prompt = self.message_entry.get("1.0", tk.END).strip()
        if not prompt:
            prompt = simpledialog.askstring("Ask Bot", "Message to chatbot:")
        if not prompt:
            return
        self.message_entry.delete("1.0", tk.END)
        self.send_command("/bot join")
        self.send_chat_text(f"@bot {prompt}")

    def send_chat_text(self, text):
        if not self.ensure_connected():
            return
        sentiment = analyze_sentiment(text)
        content = f"{text} [{sentiment}]"
        try:
            self.socket.sendall(
                encode_message(
                    "chat",
                    self.username,
                    content,
                    conversation_type=self.current_conversation_type,
                    conversation_id=self.current_conversation_id,
                    target=self.current_target,
                )
            )
        except (OSError, ProtocolError):
            self.display_message("Client", "Message failed to send.", "system")

    def open_game_window(self):
        if not self.ensure_connected():
            return
        if self.game_window and self.game_window.winfo_exists():
            self.game_window.lift()
            return

        self.game_window = tk.Toplevel(self.root)
        self.game_window.title("Tic-Tac-Toe")
        self.game_window.geometry("360x460")
        self.game_window.resizable(False, False)
        self.game_window.protocol("WM_DELETE_WINDOW", self.close_game_window)

        self.game_status = tk.Label(
            self.game_window,
            text="Click Join Game to find an opponent.",
            wraplength=320,
            font=("Arial", 12),
            pady=12,
        )
        self.game_status.pack(fill=tk.X)

        self.game_symbol_label = tk.Label(self.game_window, text="You are: -", font=("Arial", 11))
        self.game_symbol_label.pack(fill=tk.X)

        board_frame = tk.Frame(self.game_window, padx=20, pady=16)
        board_frame.pack()
        self.game_buttons = []
        for row in range(3):
            button_row = []
            for col in range(3):
                button = tk.Button(
                    board_frame,
                    text="",
                    width=5,
                    height=2,
                    font=("Arial", 24, "bold"),
                    command=lambda r=row, c=col: self.send_game_move(r, c),
                )
                button.grid(row=row, column=col, padx=5, pady=5)
                button_row.append(button)
            self.game_buttons.append(button_row)

        controls = tk.Frame(self.game_window, pady=8)
        controls.pack(fill=tk.X)
        tk.Button(controls, text="Join Game", command=self.join_game).pack(side=tk.LEFT, expand=True, padx=12)
        tk.Button(controls, text="Leave", command=self.close_game_window).pack(side=tk.LEFT, expand=True, padx=12)

        self.reset_game_board()

    def join_game(self):
        if not self.ensure_connected():
            return
        self.current_game_id = ""
        self.current_game_over = False
        self.reset_game_board()
        self.set_game_status("Waiting for another player...")
        try:
            self.socket.sendall(encode_message("game_join", self.username, ""))
        except (OSError, ProtocolError):
            self.set_game_status("Failed to join game.")

    def send_game_move(self, row, col):
        if not self.ensure_connected():
            return
        if not self.current_game_id or self.current_game_over:
            self.set_game_status("Join a game before making a move.")
            return
        try:
            self.socket.sendall(
                encode_message(
                    "game_move",
                    self.username,
                    "",
                    metadata={"game_id": self.current_game_id, "row": row, "col": col},
                )
            )
        except (OSError, ProtocolError):
            self.set_game_status("Failed to send move.")

    def handle_game_message(self, message):
        message_type = message.get("type")
        metadata = message.get("metadata", {})
        if message_type == "game_waiting":
            self.open_game_window()
            self.set_game_status(message.get("content", "Waiting for another player..."))
            return
        if message_type == "game_error":
            self.open_game_window()
            self.set_game_status(message.get("content", "Game error."))
            return

        self.open_game_window()
        self.current_game_id = metadata.get("game_id", self.current_game_id)
        self.current_game_over = bool(metadata.get("over"))
        symbol = metadata.get("symbol", "-")
        opponent = metadata.get("opponent", "")
        board = metadata.get("board", [["", "", ""], ["", "", ""], ["", "", ""]])
        turn = metadata.get("turn", "")
        winner = metadata.get("winner", "")

        self.game_symbol_label.config(text=f"You are: {symbol}    Opponent: {opponent or '-'}")
        self.update_game_board(board)

        if message_type == "game_start":
            self.set_game_status(f"Game started. {turn}'s turn.")
        elif message_type == "game_state":
            self.set_game_status(f"{turn}'s turn.")
        elif message_type == "game_over":
            if winner == "Draw":
                self.set_game_status("Game over: draw.")
            elif winner == self.username:
                self.set_game_status("Game over: you won!")
            else:
                self.set_game_status(f"Game over: {winner} won.")

    def update_game_board(self, board):
        for row in range(3):
            for col in range(3):
                value = board[row][col] if row < len(board) and col < len(board[row]) else ""
                self.game_buttons[row][col].config(text=value)

    def reset_game_board(self):
        for row in self.game_buttons:
            for button in row:
                button.config(text="")
        if self.game_symbol_label:
            self.game_symbol_label.config(text="You are: -")

    def set_game_status(self, text):
        if self.game_status:
            self.game_status.config(text=text)

    def close_game_window(self):
        if self.connected and self.current_game_id:
            try:
                self.socket.sendall(encode_message("game_leave", self.username, ""))
            except (OSError, ProtocolError):
                pass
        self.current_game_id = ""
        self.current_game_over = False
        if self.game_window and self.game_window.winfo_exists():
            self.game_window.destroy()
        self.game_window = None

    def refresh_room_list(self):
        self.room_list.delete(0, tk.END)
        for room_id, name in self.rooms.items():
            self.room_list.insert(tk.END, name)
            self.conversation_titles[room_id] = name

    def refresh_user_list(self):
        self.user_list.delete(0, tk.END)
        for name in self.online_users:
            label = f"{name} (me)" if name == self.username else name
            self.user_list.insert(tk.END, label)

    def on_room_selected(self, _event):
        selection = self.room_list.curselection()
        if not selection:
            return
        room_ids = list(self.rooms.keys())
        self.select_group(room_ids[selection[0]])

    def on_user_selected(self, _event):
        selection = self.user_list.curselection()
        if not selection:
            return
        target = self.online_users[selection[0]]
        if target == self.username:
            return
        self.select_direct(target)

    def select_group(self, room_id):
        self.current_conversation_type = "group"
        self.current_conversation_id = room_id
        self.current_target = ""
        title = self.rooms.get(room_id, PUBLIC_ROOM_NAME)
        self.conversation_titles[room_id] = title
        self.conversation_label.config(text=title)
        self.conversation_hint.config(text="Group chat")
        self.render_current_conversation()

    def select_direct(self, target):
        self.current_conversation_type = "direct"
        self.current_target = target
        self.current_conversation_id = self.direct_conversation_id(self.username, target)
        self.conversation_titles[self.current_conversation_id] = target
        self.conversation_label.config(text=target)
        self.conversation_hint.config(text="Direct message")
        self.render_current_conversation()

    def resolve_message_conversation(self, message):
        if message.get("conversation_type") == "direct":
            participants = message.get("metadata", {}).get("participants", [])
            if len(participants) == 2:
                other = participants[0] if participants[1] == self.username else participants[1]
                self.conversation_titles[message["conversation_id"]] = other
            return message.get("conversation_id")
        return message.get("conversation_id") or PUBLIC_ROOM_ID

    def direct_conversation_id(self, first_user, second_user):
        return "direct:" + "|".join(sorted([first_user, second_user]))

    def render_current_conversation(self):
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.delete("1.0", tk.END)
        for sender, content, tag in self.conversation_messages.get(self.current_conversation_id, []):
            self.chat_area.insert(tk.END, f"{sender}: {content}\n", tag)
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def generate_image_dialog(self):
        """Show dialog for image generation."""
        if not self.ensure_connected():
            return
        prompt = simpledialog.askstring(
            "Generate Image",
            "Enter image prompt (e.g., 'a beautiful sunset over mountains'):"
        )
        if prompt:
            self.send_command(f"/image {prompt}")

    def analyze_sentiment_dialog(self):
        """Show dialog for sentiment analysis."""
        if not self.ensure_connected():
            return
        text = simpledialog.askstring(
            "Analyze Sentiment",
            "Enter text to analyze:"
        )
        if text:
            self.send_command(f"/sentiment {text}")

    def handle_image_message(self, message):
        """Handle image message and display it."""
        try:
            metadata = message.get("metadata", {})
            image_b64 = metadata.get("image_data", "")
            prompt = metadata.get("prompt", "Generated Image")
            
            if not PIL_AVAILABLE:
                messagebox.showinfo("Image Generated", f"Image generated successfully!\n\nPrompt: {prompt}\n\nNote: Install PIL/Pillow to view images: pip install pillow")
                return
            
            if image_b64:
                # Decode image data
                image_data = base64.b64decode(image_b64)
                img = Image.open(BytesIO(image_data))
                
                # Create a new window to display the image
                img_window = tk.Toplevel(self.root)
                img_window.title(f"Image: {prompt}")
                
                # Resize image for display (max 600x600)
                img.thumbnail((600, 600), Image.Resampling.LANCZOS)
                
                # Convert PIL image to PhotoImage
                photo = ImageTk.PhotoImage(img)
                
                label = tk.Label(img_window, image=photo)
                label.image = photo  # Keep a reference
                label.pack(padx=10, pady=10)
                
                info_label = tk.Label(img_window, text=f"Prompt: {prompt}", wraplength=400)
                info_label.pack(padx=10, pady=5)
        except Exception as e:
            messagebox.showerror("Image Error", f"Failed to display image: {str(e)}")

    def close(self):
        self.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()
