# 04: Tools & Agent Loop

> **Key Insight**: The agent loop turns a chatbot into an agent — call tools until done.

## What's New vs 03

- 4 tools: `run_command`, `read_file`, `write_file`, `web_search`
- The agent loop — keeps calling Claude until it stops requesting tools
- Content serialization for safe session storage
- Tool dispatch pattern

## What You'll Learn

- How tool definitions work in the Anthropic API
- The agent loop pattern (the most important pattern in AI agents)
- How to serialize mixed content (text + tool calls) for persistence
- The execute/dispatch pattern for routing tool calls

## Tool Table

| Tool | Description | Example Use |
|------|-------------|-------------|
| `run_command` | Execute a shell command | "List files in the current directory" |
| `read_file` | Read file contents | "Show me the contents of bot.py" |
| `write_file` | Create/overwrite a file | "Create a hello.py script" |
| `web_search` | Search the web (placeholder) | "Search for Python best practices" |

## Prerequisites

- Completed module 03
- Anthropic API key and Telegram bot token in `.env`

## How to Run

```bash
make 04-tools-agent-loop
# or
uv run python 04-tools-agent-loop/bot.py
```

## What to Observe

1. **The bot takes actions** — Ask it to create a file and it actually does
2. **Multiple tool calls** — Complex tasks may trigger several tool calls in sequence
3. **The loop** — Watch the console output to see tool calls being executed

## Files

| File | Lines | Description |
|------|-------|-------------|
| [`bot.py`](./bot.py) | ~200 lines | Bot with tools and agent loop |

## Next Module

Ready for safety? -> [05: Permission Controls](../05-permission-controls/README.md)
