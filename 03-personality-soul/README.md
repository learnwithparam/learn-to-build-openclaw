# 03: Personality & Soul

> **Key Insight**: The system prompt IS the agent's identity.

## What's New vs 02

- `SOUL.md` — A separate file that defines the bot's personality, boundaries, and behavior
- Loaded as the `system` parameter in the API call
- Consistent identity across all conversations and users

## What You'll Learn

- How system prompts shape AI behavior
- Why separating identity into its own file is a powerful pattern
- How to design behavioral boundaries in plain text

## Prerequisites

- Completed module 02
- Anthropic API key and Telegram bot token in `.env`

## How to Run

```bash
make 03-personality-soul
# or
uv run python 03-personality-soul/bot.py
```

## What to Observe

1. **Consistent personality** — The bot behaves according to SOUL.md in every conversation
2. **Boundaries work** — Try asking it to do things outside its boundaries
3. **Edit and reload** — Change SOUL.md, restart the bot, see different behavior

## Files

| File | Lines | Description |
|------|-------|-------------|
| [`bot.py`](./bot.py) | ~90 lines | Bot with SOUL-driven identity |
| [`SOUL.md`](./SOUL.md) | ~20 lines | The bot's personality definition |

## Next Module

Ready for tools? -> [04: Tools & Agent Loop](../04-tools-agent-loop/README.md)
