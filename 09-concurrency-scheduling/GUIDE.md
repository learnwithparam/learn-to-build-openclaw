# 09 Guide: Concurrency & Scheduling

## The Race Condition Problem

With Telegram and HTTP running simultaneously (module 06), two messages for the same user can arrive at the same time:

```
Thread A: load_session("user123")     -> [msg1, msg2, msg3]
Thread B: load_session("user123")     -> [msg1, msg2, msg3]
Thread A: append msg4, save           -> [msg1, msg2, msg3, msg4]
Thread B: append msg5, save           -> [msg1, msg2, msg3, msg5]  ← msg4 is LOST!
```

Both threads loaded the same state. Thread B's save overwrites Thread A's save. Message 4 is gone.

## Per-Session Locking

```python
session_locks = defaultdict(threading.Lock)

def run_agent_turn(user_id, user_text):
    with session_locks[user_id]:  # Lock THIS user's session
        # Only one thread can be here for this user_id
        messages = load_session(user_id)
        ...
        save_session(user_id, messages)
```

Key design choice: **per-session**, not global.

| Approach | Behavior |
|----------|----------|
| Global lock | Only one user at a time. Everyone waits. |
| Per-session lock | Users don't block each other. Only concurrent messages for the SAME user wait. |
| No lock | Fast but data corruption risk. |

Per-session is the right balance: user A and user B can chat simultaneously, but user A's concurrent messages are serialized.

## The Heartbeat Pattern

Scheduled tasks let the agent do work without being prompted:

```python
def heartbeat_task():
    user_id = "cron:daily-summary"  # Isolated session
    run_agent_turn(user_id, "Check for pending tasks and write a status summary.")

schedule.every(24).hours.do(heartbeat_task)
```

Use cases:
- **Daily summaries** — Review the day's activity
- **Reminders** — Check memory for upcoming deadlines
- **Monitoring** — Check system health, report issues
- **Cleanup** — Compact old sessions, archive memory

## Cron Session Isolation

Cron tasks use `cron:{task_name}` as the user_id:

```
sessions/
    12345678.jsonl          <- Real user
    cron:daily-summary.jsonl <- Cron task
    cron:cleanup.jsonl       <- Another cron task
```

Each cron task gets its own session so:
- Cron messages don't pollute user conversations
- Each task has its own conversation context
- Tasks can be inspected independently

## The Scheduler Thread

```python
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()
```

The `schedule` library is simple: you define jobs, and `run_pending()` executes any that are due. The daemon thread means it dies when the main process exits — no zombie threads.

## Threading Architecture

```
Main Thread (Telegram polling)
    |
    +-- Daemon Thread (Flask HTTP server)
    |
    +-- Daemon Thread (Schedule runner)
    |
    +-- Per-session locks (shared across all threads)
```

All threads share the same `session_locks` dictionary and the same `execute_tool` functions. Locking ensures they don't corrupt each other's data.

---

**Locks prevent corruption. Schedules enable autonomy. Together, the agent runs reliably 24/7.**

[<- README](./README.md) | [Next: Multi-Agent Integration ->](../10-multi-agent-integration/GUIDE.md)
