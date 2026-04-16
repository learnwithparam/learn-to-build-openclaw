# 02 Guide: Persistent Sessions

## The Problem

Module 01's bot is stateless — every message is independent. But real conversations need context. When you say "Make it shorter," the assistant needs to know what "it" refers to.

The Anthropic API is also stateless. It doesn't remember previous calls. The `messages` array you send IS the conversation history. If you want multi-turn conversations, you must store and replay the full history.

## Why JSONL

JSONL (JSON Lines) stores one JSON object per line:

```
{"role": "user", "content": "My name is Alice"}
{"role": "assistant", "content": "Nice to meet you, Alice!"}
{"role": "user", "content": "What's my name?"}
{"role": "assistant", "content": "Your name is Alice."}
```

Why JSONL over alternatives?

| Format | Append-safe | Human-readable | Partial-write safe |
|--------|-------------|----------------|--------------------|
| JSON file | No (must rewrite entire file) | Yes | No (corrupts on crash) |
| JSONL | Yes (just append a line) | Yes | Yes (worst case: lose last line) |
| SQLite | Yes | No (binary) | Yes (WAL mode) |
| Pickle | No | No | No |

JSONL wins because:
- **Append-only**: Just open the file in append mode and write a line
- **Crash-safe**: If the process dies mid-write, you lose at most the last line
- **Human-readable**: You can `cat` the file to debug
- **Simple**: No libraries needed beyond `json`

## Session File Layout

Each user gets their own file: `sessions/{user_id}.jsonl`

```
sessions/
    12345678.jsonl    <- User with Telegram ID 12345678
    87654321.jsonl    <- Different user
```

User IDs come from Telegram (`update.effective_user.id`). This gives natural per-user isolation without any extra logic.

## The Load/Append Pattern

```python
def load_session(user_id):
    # Read all lines, parse each as JSON
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def append_message(user_id, message):
    # Append one JSON line
    with open(path, "a") as f:
        f.write(json.dumps(message) + "\n")
```

Key design choice: we append each message individually rather than rewriting the whole file. This means:
- Two writes per interaction (user message + assistant response)
- If the bot crashes after saving the user message but before the assistant response, on reload the session has an unanswered user message — which is fine, the next API call will generate a response

## What's Still Missing

The session grows forever. After hundreds of messages, you'll hit the model's context window limit. Module 07 (Context Compaction) solves this with automatic summarization.

---

**Append a line, read all lines. That's the whole persistence model.**

[<- README](./README.md) | [Next: Personality & Soul ->](../03-personality-soul/GUIDE.md)
