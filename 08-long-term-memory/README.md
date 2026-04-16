# 08: Long-Term Memory

> **Key Insight**: Sessions remember conversations. Memory remembers knowledge.

## What's New vs 07

- `save_memory` tool — Stores facts as markdown files in `./memory/`
- `memory_search` tool — Keyword-based search across memory files
- Updated SOUL with memory instructions (proactive saving, search before answering)
- Knowledge persists even after session reset or compaction

## What You'll Learn

- The distinction between session memory and long-term memory
- File-based memory storage with markdown
- Keyword search as a simple retrieval mechanism
- How to instruct the agent to use memory proactively via the SOUL

## Prerequisites

- Completed module 07
- Anthropic API key and Telegram bot token in `.env`

## How to Run

```bash
make 08-long-term-memory
# or
uv run python 08-long-term-memory/bot.py
```

## What to Observe

1. **Proactive memory saving** — Tell the bot facts and watch it use `save_memory` automatically
2. **Cross-session recall** — Delete the session file, restart, ask about saved facts
3. **Memory files** — Check the `memory/` directory to see stored knowledge

## Files

| File | Lines | Description |
|------|-------|-------------|
| [`bot.py`](./bot.py) | ~400 lines | Bot with long-term memory system |

## Next Module

Ready for concurrency? -> [09: Concurrency & Scheduling](../09-concurrency-scheduling/README.md)
