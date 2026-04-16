# 06 Guide: Gateway

## The Gateway Pattern

Until now, the bot was tightly coupled to Telegram. But the core logic — load session, call Claude, save response — has nothing to do with Telegram. The gateway pattern makes this explicit:

```
Telegram Handler ──┐
                   ├──> run_agent_turn(user_id, text) ──> Claude API
HTTP Endpoint ─────┘
CLI REPL ──────────┘  (Exercise: add this!)
```

Each channel is just a thin adapter that:
1. Extracts `user_id` and `text` from the incoming message
2. Calls `run_agent_turn(user_id, text)`
3. Sends the reply back through its channel

## Why Sessions Are Keyed by user_id

Sessions are stored as `sessions/{user_id}.jsonl`. The `user_id` comes from:
- **Telegram**: `update.effective_user.id` (e.g., "12345678")
- **HTTP**: Whatever the client passes in the request body

If you use the same `user_id` from both channels, you get the same conversation. This means a user can start chatting on Telegram and continue via HTTP (or vice versa).

This is a deliberate design choice. The alternative — keying by `{channel}:{user_id}` — would create separate conversations per channel.

## Threading Model

```python
def main():
    # HTTP runs in a daemon thread
    http_thread = threading.Thread(target=start_http, daemon=True)
    http_thread.start()

    # Telegram runs in the main thread
    start_telegram()
```

Why this arrangement:
- **Telegram** uses `asyncio` internally (via `python-telegram-bot`), so it needs the main thread's event loop
- **Flask** runs its own server, so it works fine in a daemon thread
- `daemon=True` means the HTTP thread dies when the main thread exits

## Race Conditions

With two channels running concurrently, two requests for the same user could arrive simultaneously. Both would:
1. Load the same session file
2. Append different messages
3. Save — one overwrites the other

This is a real problem. Module 09 solves it with per-session locking. For now, it's unlikely to cause issues in practice (human typing speed is slow), but it's worth understanding the risk.

## Config-Driven Channel Startup

In production, you'd make channels configurable:

```python
CHANNELS = {
    "telegram": {"enabled": True, "token": os.environ.get("TELEGRAM_BOT_TOKEN")},
    "http": {"enabled": True, "port": 5000},
    "slack": {"enabled": False},
}
```

Start only enabled channels, skip those without credentials. The gateway pattern makes adding new channels trivial — just write a new thin adapter.

---

**The agent doesn't care where messages come from. That's the power of the gateway.**

[<- README](./README.md) | [Next: Context Compaction ->](../07-context-compaction/GUIDE.md)
