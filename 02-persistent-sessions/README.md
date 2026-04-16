# 02: Persistent Sessions

> **Key Insight**: JSONL is the simplest crash-safe persistence format.

## What's New vs 01

- Per-user session files in `./sessions/{user_id}.jsonl`
- Multi-turn conversation memory that survives restarts
- Append-only persistence (crash-safe — partial writes don't corrupt)

## What You'll Learn

- How to persist conversation history to disk
- Why JSONL (one JSON object per line) is ideal for append-only logs
- How per-user isolation works with file-based sessions

## Prerequisites

- Completed module 01
- Anthropic API key and Telegram bot token in `.env`

## How to Run

```bash
make 02-persistent-sessions
# or
uv run python 02-persistent-sessions/bot.py
```

## Directory Structure

```
02-persistent-sessions/
    bot.py
    sessions/           <- Created automatically
        12345.jsonl     <- One file per Telegram user ID
        67890.jsonl
```

## What to Observe

1. **Memory persists** — Tell the bot your name, then ask "What's my name?" — it remembers
2. **Survives restarts** — Stop the bot (Ctrl+C), restart it, ask again — still remembers
3. **Per-user isolation** — Each Telegram user gets their own session file

## Files

| File | Lines | Description |
|------|-------|-------------|
| [`bot.py`](./bot.py) | ~80 lines | Bot with JSONL session persistence |

## Next Module

Ready for personality? -> [03: Personality & Soul](../03-personality-soul/README.md)
