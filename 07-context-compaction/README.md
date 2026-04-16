# 07: Context Compaction

> **Key Insight**: Summarize the old, keep the recent, never hit the limit.

## What's New vs 06

- `estimate_tokens()` — Heuristic token counting (chars / 4)
- `compact_session()` — Summarizes old messages, keeps recent ones verbatim
- Automatic compaction triggered when token count exceeds threshold
- Session file gets rewritten with compacted history

## What You'll Learn

- Why context windows have limits and what happens when you hit them
- The split-summarize-merge compaction strategy
- Token estimation heuristics
- What information survives compaction and what gets lost

## Prerequisites

- Completed module 06
- Anthropic API key and Telegram bot token in `.env`

## How to Run

```bash
make 07-context-compaction
# or
uv run python 07-context-compaction/bot.py
```

## What to Observe

1. **Long conversations work** — The bot handles conversations that would exceed the context window
2. **Key facts survive** — Information from early in the conversation is preserved in summaries
3. **Recent context is verbatim** — The last N messages are kept exactly as-is

## Files

| File | Lines | Description |
|------|-------|-------------|
| [`bot.py`](./bot.py) | ~350 lines | Bot with automatic context compaction |

## Next Module

Ready for persistent memory? -> [08: Long-Term Memory](../08-long-term-memory/README.md)
