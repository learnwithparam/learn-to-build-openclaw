# 10: Multi-Agent Integration

> **Key Insight**: Specialize agents, share memory — that's collaboration.

## What's New vs 09

- `AGENTS` config dict — Multiple agents with different SOULs and tool sets
- `resolve_agent()` — Prefix-based routing (`/research` triggers the research agent)
- Per-agent sessions — `{user_id}:{agent_name}` isolation
- Shared memory — All agents read/write the same memory directory
- REPL interface — Local testing without Telegram
- `~/.mini-openclaw/` workspace

## What You'll Learn

- The agent config pattern for defining specialized agents
- Prefix-based message routing
- How separate sessions + shared memory = collaboration
- The full architecture: sessions, SOUL, tools, permissions, compaction, memory, locking, scheduling, and routing

## Agents

| Agent | Prefix | Specialization |
|-------|--------|----------------|
| General | (default) | General-purpose assistant, runs commands, manages files |
| Research | `/research` | In-depth analysis, structured findings, no file writing |

## Prerequisites

- Completed module 09
- Anthropic API key in `.env`

## How to Run

```bash
make 10-multi-agent-integration
# or
uv run python 10-multi-agent-integration/mini-openclaw.py
```

## What to Observe

1. **Default routing** — Normal messages go to the general agent
2. **Prefix routing** — `/research analyze this codebase` goes to the research agent
3. **Shared memory** — Research findings saved by the research agent are visible to the general agent
4. **Separate sessions** — Each agent has its own conversation history

## Workspace

```
~/.mini-openclaw/
    sessions/
        repl-user:general.jsonl
        repl-user:research.jsonl
        cron:heartbeat:general.jsonl
    memory/
        user-preferences.md
        research-findings.md
    exec-approvals.json
```

## Files

| File | Lines | Description |
|------|-------|-------------|
| [`mini-openclaw.py`](./mini-openclaw.py) | ~400 lines | The full mini-OpenClaw system |

## The Full Architecture

```
User Input
    |
    v
[resolve_agent] ── prefix match ──> Agent Config (SOUL, tools)
    |
    v
[session_locks] ── per-session lock
    |
    v
[load_session] ── JSONL per user:agent
    |
    v
[estimate_tokens] ── compact if needed
    |
    v
[Agent Loop]
    |── Claude API (with SOUL + tools)
    |── execute_tool() with permission checks
    |── save_memory / memory_search (shared)
    |── Loop until stop_reason != tool_use
    |
    v
[save_session] ── persist to disk
    |
    v
Reply to user
```

This is the complete system. Every module added one piece:
1. API call (01) -> 2. Sessions (02) -> 3. SOUL (03) -> 4. Tools (04) -> 5. Permissions (05) -> 6. Gateway (06) -> 7. Compaction (07) -> 8. Memory (08) -> 9. Concurrency (09) -> 10. Multi-agent (10)
