import json


ENCODING = "utf-8"


def encode_message(message_type, sender, content, **extra):
    payload = {
        "type": message_type,
        "sender": sender,
        "content": content,
    }
    payload.update(extra)
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode(ENCODING)


def decode_messages(buffer):
    messages = []
    while b"\n" in buffer:
        line, buffer = buffer.split(b"\n", 1)
        if not line.strip():
            continue
        messages.append(json.loads(line.decode(ENCODING)))
    return messages, buffer
