# 09: Concurrency & Scheduling

> **Key Insight**: Lock per session, schedule per task — the agent never sleeps.

## What's New vs 08

- `session_locks` — Per-session `threading.Lock` prevents race conditions
- `setup_heartbeats()` — Scheduled periodic tasks using the `schedule` library
- Cron session isolation — Scheduled tasks use `cron:{task_name}` as user_id
- Daemon thread for the scheduler loop

## What You'll Learn

- Why concurrent channels create race conditions
- Per-session locking vs global locking tradeoffs
- The heartbeat/cron pattern for scheduled agent tasks
- How cron tasks get their own isolated sessions

## Prerequisites

- Completed module 08
- Anthropic API key and Telegram bot token in `.env`

## How to Run

```bash
make 09-concurrency-scheduling
# or
uv run python 09-concurrency-scheduling/bot.py
```

## What to Observe

1. **Safe concurrent access** — Send messages from Telegram and HTTP simultaneously
2. **Scheduler running** — Watch for `[cron]` log messages
3. **Isolated cron sessions** — Check `sessions/cron:daily-summary.jsonl`

## Files

| File | Lines | Description |
|------|-------|-------------|
| [`bot.py`](./bot.py) | ~450 lines | Bot with per-session locks and scheduled tasks |

## Next Module

Ready for the full system? -> [10: Multi-Agent Integration](../10-multi-agent-integration/README.md)
