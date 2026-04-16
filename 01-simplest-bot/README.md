# 01: The Simplest Bot

> **Key Insight**: An AI bot is just an API call wrapped in a message handler.

## What You'll Learn

- How to connect a Telegram bot to the Anthropic API
- That a working AI assistant can be built in ~20 lines
- Why statelessness is a problem you'll solve in the next module

## Prerequisites

- Python 3.10+ installed
- Anthropic API key and Telegram bot token configured in `.env`
- `make install` completed

## How to Run

```bash
make 01-simplest-bot
# or
uv run python 01-simplest-bot/bot.py
```

Then open Telegram and send a message to your bot.

## What to Observe

1. **It works** — Your bot responds intelligently to any message
2. **It forgets** — Send "My name is Alice" then "What's my name?" — it won't remember
3. **Each message is independent** — No conversation context carries over

## Key Concept

```
User Message → Telegram → bot.py → Anthropic API → Reply
```

No history, no state, no persistence. Just a single API call per message.

## Files

| File | Lines | Description |
|------|-------|-------------|
| [`bot.py`](./bot.py) | ~20 lines | The complete stateless bot |

## Next Module

Ready for memory? -> [02: Persistent Sessions](../02-persistent-sessions/README.md)
