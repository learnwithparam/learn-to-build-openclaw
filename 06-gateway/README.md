# 06: Gateway

> **Key Insight**: The agent logic is channel-agnostic — same function, any interface.

## What's New vs 05

- Flask HTTP endpoint (`POST /chat`) alongside Telegram
- Both channels call the same `run_agent_turn()` function
- Sessions keyed by `user_id` — shared across channels
- Threading for concurrent channel operation

## What You'll Learn

- The gateway pattern: decoupling agent logic from delivery channels
- Why sessions are keyed by `user_id`, not by channel
- How to run multiple interfaces (Telegram + HTTP) concurrently
- Threading model for multi-channel bots

## Prerequisites

- Completed module 05
- Anthropic API key and Telegram bot token in `.env`

## How to Run

```bash
make 06-gateway
# or
uv run python 06-gateway/bot.py
```

### Test via Telegram
Send a message to your bot as usual.

### Test via HTTP
```bash
curl -X POST http://localhost:5000/chat \
  -H 'Content-Type: application/json' \
  -d '{"user_id": "test-user", "message": "Hello!"}'
```

## What to Observe

1. **Same agent, two interfaces** — Chat via Telegram and HTTP, both work identically
2. **Shared sessions** — Use the same `user_id` in HTTP that Telegram assigns, and the conversation continues
3. **Concurrent operation** — Both channels run simultaneously

## Files

| File | Lines | Description |
|------|-------|-------------|
| [`bot.py`](./bot.py) | ~300 lines | Multi-channel gateway bot |

## Next Module

Ready for context management? -> [07: Context Compaction](../07-context-compaction/README.md)
