import json


ENCODING = "utf-8"
MAX_MESSAGE_BYTES = 4 * 1024 * 1024


class ProtocolError(ValueError):
    pass


def encode_message(message_type, sender, content, **extra):
    conversation_type = extra.pop("conversation_type", "group")
    conversation_id = extra.pop("conversation_id", "public")
    target = extra.pop("target", "")
    metadata = extra.pop("metadata", {})
    payload = {
        "type": message_type,
        "sender": sender,
        "content": content,
        "conversation_type": conversation_type,
        "conversation_id": conversation_id,
        "target": target,
        "metadata": metadata,
    }
    payload.update(extra)
    encoded = (json.dumps(payload, ensure_ascii=False) + "\n").encode(ENCODING)
    if len(encoded) > MAX_MESSAGE_BYTES:
        raise ProtocolError("Message is too large.")
    return encoded


def decode_messages(buffer):
    if len(buffer) > MAX_MESSAGE_BYTES:
        raise ProtocolError("Buffered message is too large.")

    messages = []
    while b"\n" in buffer:
        line, buffer = buffer.split(b"\n", 1)
        if not line.strip():
            continue
        if len(line) > MAX_MESSAGE_BYTES:
            raise ProtocolError("Message line is too large.")
        try:
            message = json.loads(line.decode(ENCODING))
        except (UnicodeDecodeError, json.JSONDecodeError):
            messages.append(
                {
                    "type": "protocol_error",
                    "sender": "Protocol",
                    "content": "Received an invalid message and ignored it.",
                    "conversation_type": "system",
                    "conversation_id": "system",
                    "target": "",
                    "metadata": {},
                }
            )
            continue
        if not isinstance(message, dict):
            continue
        message.setdefault("conversation_type", "group")
        message.setdefault("conversation_id", "public")
        message.setdefault("target", "")
        message.setdefault("metadata", {})
        messages.append(message)
    return messages, buffer
