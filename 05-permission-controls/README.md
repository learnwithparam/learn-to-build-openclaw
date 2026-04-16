# 05: Permission Controls

> **Key Insight**: Safety is a persistent allowlist, not a per-request prompt.

## What's New vs 04

- `SAFE_COMMANDS` set — Commands always allowed without approval
- `DANGEROUS_PATTERNS` list — Commands always blocked (regex patterns)
- `check_command_safety()` — Three-tier classification: safe / needs_approval / blocked
- `exec-approvals.json` — Persistent file of previously approved commands

## What You'll Learn

- The three-tier safety model for command execution
- Why persistent approvals are better than per-request prompts
- How regex patterns catch dangerous command patterns
- Designing safety systems that don't annoy users

## The Three Tiers

```
Command arrives
    |
    v
[Dangerous pattern?] --yes--> BLOCKED (always)
    |no
    v
[Safe command?] ------yes--> ALLOWED (always)
    |no
    v
[Previously approved?] -yes-> ALLOWED
    |no
    v
NEEDS APPROVAL --> auto-approve + save for next time
```

## Prerequisites

- Completed module 04
- Anthropic API key and Telegram bot token in `.env`

## How to Run

```bash
make 05-permission-controls
# or
uv run python 05-permission-controls/bot.py
```

## What to Observe

1. **Safe commands run immediately** — `ls`, `cat`, `python` need no approval
2. **Dangerous commands are blocked** — `rm -rf /` will never execute
3. **Unknown commands get auto-approved** — First use is approved, saved for next time
4. **Check exec-approvals.json** — See what's been approved

## Files

| File | Lines | Description |
|------|-------|-------------|
| [`bot.py`](./bot.py) | ~250 lines | Bot with three-tier permission system |

## Next Module

Ready for multi-channel? -> [06: Gateway](../06-gateway/README.md)
