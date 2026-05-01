import socket
import threading
from collections import Counter, deque

from chatbot import (
    OpenAICompatibleBot, 
    extract_keywords, 
    extract_summary,
    generate_image_pollinations,
    analyze_sentiment,
    analyze_sentiment_textblob
)
from protocol import ProtocolError, decode_messages, encode_message


HOST = "0.0.0.0"
PORT = 5001
PUBLIC_ROOM_ID = "public"
PUBLIC_ROOM_NAME = "Public Chat"
BOT_NAME = "Bot"


class ChatServer:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.clients = {}
        self.user_sockets = {}
        self.clients_lock = threading.Lock()
        self.histories = {PUBLIC_ROOM_ID: deque(maxlen=100)}
        self.rooms = {PUBLIC_ROOM_ID: PUBLIC_ROOM_NAME}
        self.bot = OpenAICompatibleBot("friendly group chat assistant")
        self.bot_lock = threading.Lock()
        self.bot_rooms = set()
        self.game_lock = threading.Lock()
        self.waiting_player = None
        self.games = {}
        self.user_games = {}
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
                    message_type = message.get("type")
                    if message_type == "protocol_error":
                        self.send_to(client_socket, "system", "Protocol", message["content"])
                    elif message_type == "login":
                        username = self.register_client(client_socket, message.get("sender", ""), address)
                    elif message_type == "chat":
                        self.handle_chat(username, message)
                    elif message_type == "command":
                        self.handle_command(client_socket, username, message)
                    elif message_type == "game_join":
                        self.handle_game_join(client_socket, username)
                    elif message_type == "game_move":
                        self.handle_game_move(client_socket, username, message)
                    elif message_type == "game_leave":
                        self.handle_game_leave(username)
        except (ConnectionError, OSError, ProtocolError):
            pass
        finally:
            self.remove_client(client_socket, username)

    def register_client(self, client_socket, requested_name, address):
        base_name = requested_name.strip() or f"Guest-{address[1]}"
        username = base_name
        with self.clients_lock:
            existing = {info["username"] for info in self.clients.values()}
            suffix = 2
            while username in existing:
                username = f"{base_name}{suffix}"
                suffix += 1
            self.clients[client_socket] = {"username": username, "address": address}
            self.user_sockets[username] = client_socket
        self.send_to(
            client_socket,
            "login_ack",
            "Server",
            f"Welcome, {username}!",
            metadata={"username": username},
        )
        self.send_user_list(client_socket)
        self.send_room_list(client_socket)
        self.broadcast(
            "system",
            "Server",
            f"{username} joined {PUBLIC_ROOM_NAME}.",
            conversation_id=PUBLIC_ROOM_ID,
        )
        self.broadcast_user_list()
        return username

    def handle_chat(self, username, message):
        if not username:
            return
        text = message.get("content", "").strip()
        if not text:
            return

        conversation_type = message.get("conversation_type", "group")
        target = message.get("target", "").strip()
        if conversation_type == "direct":
            self.handle_direct_chat(username, target, text)
            return

        conversation_id = message.get("conversation_id") or PUBLIC_ROOM_ID
        if conversation_id not in self.rooms:
            conversation_id = PUBLIC_ROOM_ID
        self.add_history(conversation_id, username, text)
        self.broadcast(
            "chat",
            username,
            text,
            conversation_type="group",
            conversation_id=conversation_id,
        )
        if self.should_bot_reply(conversation_id, text):
            prompt = self.extract_bot_prompt(username, text)
            threading.Thread(
                target=self.reply_as_group_bot,
                args=(conversation_id, prompt),
                daemon=True,
            ).start()

    def handle_direct_chat(self, username, target, text):
        with self.clients_lock:
            sender_socket = self.user_sockets.get(username)
            target_socket = self.user_sockets.get(target)
        if not target_socket:
            if sender_socket:
                self.send_to(sender_socket, "system", "Server", f"{target or 'User'} is not online.")
            return
        conversation_id = self.direct_conversation_id(username, target)
        self.add_history(conversation_id, username, text)
        for socket_obj in {sender_socket, target_socket}:
            if socket_obj:
                self.send_to(
                    socket_obj,
                    "chat",
                    username,
                    text,
                    conversation_type="direct",
                    conversation_id=conversation_id,
                    target=target,
                    metadata={"participants": sorted([username, target])},
                )

    def handle_command(self, client_socket, username, message):
        raw_command = message.get("content", "").strip()
        command = raw_command.lower()
        conversation_id = message.get("conversation_id") or PUBLIC_ROOM_ID
        if command == "/who":
            with self.clients_lock:
                names = sorted(info["username"] for info in self.clients.values())
            self.send_to(client_socket, "system", "Server", "Online: " + ", ".join(names))
            self.send_user_list(client_socket)
        elif command == "/summary":
            self.send_to(client_socket, "system", "Summary", self.make_summary(conversation_id))
        elif command == "/summary_nlp":
            self.send_to(client_socket, "system", "Summary (NLP)", self.make_summary_nlp(conversation_id))
        elif command == "/keywords":
            self.send_to(client_socket, "system", "Keywords", self.make_keywords(conversation_id))
        elif command.startswith("/image "):
            prompt = raw_command[len("/image "):].strip()
            threading.Thread(
                target=self.generate_and_send_image,
                args=(client_socket, prompt, conversation_id),
                daemon=True,
            ).start()
        elif command.startswith("/sentiment "):
            text = raw_command[len("/sentiment "):].strip()
            sentiment_info = analyze_sentiment_textblob(text)
            result = f"Sentiment: {sentiment_info['sentiment']} {sentiment_info['emoji']} (Polarity: {sentiment_info['polarity']})"
            self.send_to(client_socket, "system", "Sentiment", result)
        elif command == "/rooms":
            self.send_room_list(client_socket)
        elif command == "/bot join":
            self.bot_rooms.add(PUBLIC_ROOM_ID)
            self.broadcast(
                "system",
                "Server",
                "Bot joined the group chat. Mention @bot to ask a question.",
                conversation_id=PUBLIC_ROOM_ID,
            )
        elif command == "/bot leave":
            self.bot_rooms.discard(PUBLIC_ROOM_ID)
            self.broadcast("system", "Server", "Bot left the group chat.", conversation_id=PUBLIC_ROOM_ID)
        elif command.startswith("/bot personality "):
            personality = raw_command[len("/bot personality "):].strip()
            self.bot.set_personality(personality)
            self.broadcast(
                "system",
                "Bot",
                f"Personality set to: {self.bot.personality}",
                conversation_id=PUBLIC_ROOM_ID,
            )
        elif command == "/bot status":
            state = "in the group" if PUBLIC_ROOM_ID in self.bot_rooms else "not in the group"
            self.send_to(client_socket, "system", "Bot", f"Bot is {state}.")
        elif command == "/help":
            self.send_to(
                client_socket,
                "system",
                "Server",
                "Commands: /who, /summary, /summary_nlp, /keywords, /image <prompt>, /sentiment <text>, "
                "/rooms, /bot join, /bot leave, /bot status, /bot personality <style>",
            )
        else:
            self.send_to(client_socket, "system", "Server", f"Unknown command: {command}")

    def add_history(self, conversation_id, username, text):
        self.histories.setdefault(conversation_id, deque(maxlen=100)).append((username, text))

    def make_summary(self, conversation_id=PUBLIC_ROOM_ID):
        recent = list(self.histories.get(conversation_id, []))[-8:]
        if not recent:
            return "No chat history yet."
        speakers = sorted({name for name, _ in recent})
        topics = extract_keywords([text for _, text in recent], limit=5)
        return f"Recent chat has {len(recent)} messages from {', '.join(speakers)}. Main topics: {', '.join(topics) or 'none'}."

    def make_keywords(self, conversation_id=PUBLIC_ROOM_ID):
        history = self.histories.get(conversation_id, [])
        words = extract_keywords([text for _, text in history], limit=8)
        return ", ".join(words) if words else "No keywords yet."

    def make_summary_nlp(self, conversation_id=PUBLIC_ROOM_ID):
        """Generate summary using NLP-based approach."""
        history = self.histories.get(conversation_id, [])
        texts = [text for _, text in history]
        if not texts:
            return "No chat history yet."
        summary = extract_summary(texts, max_sentences=3)
        return summary

    def generate_and_send_image(self, client_socket, prompt, conversation_id):
        """Generate image using Pollinations.ai and send to client."""
        try:
            self.send_to(client_socket, "system", "Image", f"Generating image for: {prompt}...")
            image_data = generate_image_pollinations(prompt)
            
            if image_data:
                import base64
                image_b64 = base64.b64encode(image_data).decode('utf-8')
                self.send_to(
                    client_socket, 
                    "image", 
                    "Image Generator", 
                    f"Image generated: {prompt}",
                    metadata={"image_data": image_b64, "prompt": prompt}
                )
            else:
                self.send_to(client_socket, "system", "Image", "Failed to generate image. Please try again.")
        except Exception as e:
            self.send_to(
            client_socket,
            "system",
            "Image",
            f"Image generation error: {type(e).__name__}: {repr(e)}",
            )

    def extract_keywords(self, texts, limit=8):
        """Fallback local method - uses imported version from chatbot module."""
        return extract_keywords(texts, limit=limit)

    def should_bot_reply(self, conversation_id, text):
        lowered = text.lower()
        return conversation_id in self.bot_rooms and ("@bot" in lowered or lowered.startswith("bot,"))

    def extract_bot_prompt(self, username, text):
        prompt = text.replace("@bot", "").replace("@Bot", "").strip(" ,:")
        return f"{username} says: {prompt or text}"

    def reply_as_group_bot(self, conversation_id, prompt):
        with self.bot_lock:
            reply = self.bot.chat(prompt)
            status = self.bot.last_status
        if status == "fallback":
            reply = f"{reply} (API unavailable, local fallback used.)"
        self.add_history(conversation_id, BOT_NAME, reply)
        self.broadcast(
            "chat",
            BOT_NAME,
            reply,
            conversation_type="group",
            conversation_id=conversation_id,
        )

    def direct_conversation_id(self, first_user, second_user):
        names = sorted([first_user, second_user])
        return "direct:" + "|".join(names)

    def handle_game_join(self, client_socket, username):
        if not username:
            return
        with self.game_lock:
            if username in self.user_games:
                game = self.games.get(self.user_games[username])
                if game:
                    self.send_game_state_to(username, game)
                return
            if self.waiting_player and self.waiting_player != username:
                first_player = self.waiting_player
                second_player = username
                self.waiting_player = None
                game_id = self.game_id_for(first_player, second_player)
                game = {
                    "game_id": game_id,
                    "players": [first_player, second_player],
                    "symbols": {first_player: "X", second_player: "O"},
                    "board": [["", "", ""], ["", "", ""], ["", "", ""]],
                    "turn": first_player,
                    "winner": None,
                    "over": False,
                }
                self.games[game_id] = game
                self.user_games[first_player] = game_id
                self.user_games[second_player] = game_id
            else:
                self.waiting_player = username
                self.send_to(
                    client_socket,
                    "game_waiting",
                    "Game",
                    "Waiting for another player to join Tic-Tac-Toe.",
                )
                return
        self.send_game_start(game)
        self.broadcast_game_state(game)

    def handle_game_move(self, client_socket, username, message):
        metadata = message.get("metadata", {})
        try:
            row = int(metadata.get("row"))
            col = int(metadata.get("col"))
        except (TypeError, ValueError):
            self.send_to(client_socket, "game_error", "Game", "Invalid move coordinates.")
            return

        with self.game_lock:
            game_id = self.user_games.get(username)
            game = self.games.get(game_id)
            error = self.validate_game_move(game, username, row, col)
            if error:
                self.send_to(client_socket, "game_error", "Game", error)
                return
            game["board"][row][col] = game["symbols"][username]
            winner_symbol = self.find_winner(game["board"])
            if winner_symbol:
                game["winner"] = self.player_for_symbol(game, winner_symbol)
                game["over"] = True
            elif self.board_full(game["board"]):
                game["winner"] = "Draw"
                game["over"] = True
            else:
                players = game["players"]
                game["turn"] = players[1] if username == players[0] else players[0]
        self.broadcast_game_state(game)
        if game["over"]:
            self.send_game_over(game)

    def handle_game_leave(self, username):
        if not username:
            return
        game = None
        with self.game_lock:
            if self.waiting_player == username:
                self.waiting_player = None
                return
            game_id = self.user_games.pop(username, None)
            if not game_id:
                return
            game = self.games.pop(game_id, None)
            if game:
                for player in game["players"]:
                    self.user_games.pop(player, None)
        if game:
            for player in game["players"]:
                if player != username:
                    self.send_game_message(player, "game_over", f"{username} left the game.", game, winner=player)

    def validate_game_move(self, game, username, row, col):
        if not game:
            return "You are not in a game."
        if game["over"]:
            return "This game is already over."
        if username not in game["players"]:
            return "You are not a player in this game."
        if game["turn"] != username:
            return "It is not your turn."
        if row not in range(3) or col not in range(3):
            return "Move is outside the board."
        if game["board"][row][col]:
            return "That cell is already taken."
        return ""

    def find_winner(self, board):
        lines = []
        lines.extend(board)
        lines.extend([[board[0][col], board[1][col], board[2][col]] for col in range(3)])
        lines.extend(
            [
                [board[0][0], board[1][1], board[2][2]],
                [board[0][2], board[1][1], board[2][0]],
            ]
        )
        for line in lines:
            if line[0] and line[0] == line[1] == line[2]:
                return line[0]
        return ""

    def board_full(self, board):
        return all(cell for row in board for cell in row)

    def player_for_symbol(self, game, symbol):
        for player, player_symbol in game["symbols"].items():
            if player_symbol == symbol:
                return player
        return ""

    def game_id_for(self, first_player, second_player):
        return "game:" + "|".join(sorted([first_player, second_player]))

    def send_game_start(self, game):
        for player in game["players"]:
            self.send_game_message(player, "game_start", "Tic-Tac-Toe game started.", game)

    def broadcast_game_state(self, game):
        for player in game["players"]:
            self.send_game_state_to(player, game)

    def send_game_state_to(self, player, game):
        self.send_game_message(player, "game_state", "Game state updated.", game)

    def send_game_over(self, game):
        winner = game["winner"]
        if winner == "Draw":
            content = "Tic-Tac-Toe ended in a draw."
        else:
            content = f"{winner} won Tic-Tac-Toe."
        for player in game["players"]:
            self.send_game_message(player, "game_over", content, game, winner=winner)
        with self.game_lock:
            self.games.pop(game["game_id"], None)
            for player in game["players"]:
                self.user_games.pop(player, None)

    def send_game_message(self, player, message_type, content, game, winner=None):
        with self.clients_lock:
            client_socket = self.user_sockets.get(player)
        if not client_socket:
            return
        opponent = next((name for name in game["players"] if name != player), "")
        self.send_to(
            client_socket,
            message_type,
            "Game",
            content,
            metadata={
                "game_id": game["game_id"],
                "players": game["players"],
                "opponent": opponent,
                "symbol": game["symbols"].get(player, ""),
                "symbols": game["symbols"],
                "board": game["board"],
                "turn": game["turn"],
                "winner": winner if winner is not None else game["winner"],
                "over": game["over"],
            },
        )

    def broadcast(self, message_type, sender, content, exclude=None, **extra):
        try:
            packet = encode_message(message_type, sender, content, **extra)
        except ProtocolError:
            return
        with self.clients_lock:
            sockets = list(self.clients.keys())
        for client_socket in sockets:
            if client_socket is exclude:
                continue
            try:
                client_socket.sendall(packet)
            except OSError:
                self.remove_client(client_socket, self.get_username(client_socket))

    def send_to(self, client_socket, message_type, sender, content, **extra):
        try:
            client_socket.sendall(encode_message(message_type, sender, content, **extra))
        except (OSError, ProtocolError):
            self.remove_client(client_socket, self.get_username(client_socket))

    def send_user_list(self, client_socket):
        with self.clients_lock:
            names = sorted(info["username"] for info in self.clients.values())
        self.send_to(client_socket, "user_list", "Server", "", metadata={"users": names})

    def broadcast_user_list(self):
        with self.clients_lock:
            names = sorted(info["username"] for info in self.clients.values())
        self.broadcast("user_list", "Server", "", metadata={"users": names})

    def send_room_list(self, client_socket):
        rooms = [{"id": room_id, "name": name} for room_id, name in self.rooms.items()]
        self.send_to(client_socket, "room_list", "Server", "", metadata={"rooms": rooms})

    def get_username(self, client_socket):
        with self.clients_lock:
            info = self.clients.get(client_socket)
            return info["username"] if info else None

    def remove_client(self, client_socket, username):
        removed = False
        with self.clients_lock:
            if client_socket in self.clients:
                removed = True
                username = self.clients.pop(client_socket)["username"]
                self.user_sockets.pop(username, None)
        try:
            client_socket.close()
        except OSError:
            pass
        if removed and username:
            self.handle_game_leave(username)
            self.broadcast("system", "Server", f"{username} left the chat.", conversation_id=PUBLIC_ROOM_ID)
            self.broadcast_user_list()


if __name__ == "__main__":
    ChatServer().start()
