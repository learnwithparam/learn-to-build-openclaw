# 10 Guide: Multi-Agent Integration

## The Agent Config Pattern

Instead of hardcoding a single agent, we define agents as configuration:

```python
AGENTS = {
    "general": {
        "name": "OpenClaw",
        "soul": "...",
        "tools": ["run_command", "read_file", "write_file", "save_memory", "memory_search"],
    },
    "research": {
        "name": "OpenClaw Research",
        "soul": "...",
        "tools": ["run_command", "read_file", "save_memory", "memory_search"],
    },
}
```

Each agent has:
- Its own SOUL (personality and instructions)
- Its own tool set (research agent can't write files)
- Its own session history

This is the same pattern used by production systems like OpenClaw, Claude Code (with subagents), and multi-agent frameworks.

## Prefix-Based Routing

```python
ROUTE_PREFIXES = {
    "/research": "research",
}

def resolve_agent(user_text):
    for prefix, agent_name in ROUTE_PREFIXES.items():
        if user_text.lower().startswith(prefix):
            return agent_name, user_text[len(prefix):].strip()
    return DEFAULT_AGENT, user_text
```

Simple and explicit. The user controls which agent handles their request. Alternatives:
- **Classifier-based** — Use an LLM to route based on intent
- **Tool-based** — The main agent delegates to sub-agents via tools
- **Keyword-based** — Pattern matching on message content

Prefix-based is the simplest and most transparent.

## Separate Sessions, Shared Memory

This is the collaboration model:

```
General Agent                    Research Agent
    |                                |
    v                                v
sessions/user:general.jsonl     sessions/user:research.jsonl
    |                                |
    +---------- SHARED ------------->+
    |                                |
    v                                v
    memory/user-preferences.md
    memory/research-findings.md
    memory/project-details.md
```

- **Sessions are separate** — Each agent has its own conversation history. The general agent doesn't see research conversations and vice versa.
- **Memory is shared** — Both agents read and write to the same `memory/` directory. Research findings are immediately available to the general agent.

This enables collaboration without cross-contamination. The research agent can do deep analysis without polluting the general agent's conversational flow, but its findings are accessible to all agents.

## Workspace Organization

The `~/.mini-openclaw/` directory mirrors how real AI assistants organize state:

```
~/.mini-openclaw/
    sessions/          <- Conversation state (volatile)
    memory/            <- Knowledge base (permanent)
    exec-approvals.json <- Permission state (persistent)
```

Using a home-directory workspace means:
- State persists across working directories
- Multiple terminals share the same state
- Easy to find and inspect

## Architecture Review: All 10 Modules

| Module | Addition | Why It Matters |
|--------|----------|----------------|
| 01 | API call | The foundation — LLM + interface |
| 02 | Sessions | Multi-turn conversations |
| 03 | SOUL | Consistent identity and boundaries |
| 04 | Tools + loop | From chatbot to agent |
| 05 | Permissions | Safe command execution |
| 06 | Gateway | Channel-agnostic architecture |
| 07 | Compaction | Infinite conversations |
| 08 | Memory | Persistent knowledge |
| 09 | Concurrency | Safe multi-threaded operation |
| 10 | Multi-agent | Specialization and collaboration |

Each module added exactly one concept. The final system is the sum of all 10.

## What a Production System Would Add

Mini-OpenClaw is ~400 lines. A production system like the real OpenClaw adds:
- **Real web search** via APIs (not placeholder)
- **Vector embeddings** for semantic memory search
- **User authentication** for multi-user deployment
- **Rate limiting** to control API costs
- **Error recovery** with retry logic
- **Monitoring** with structured logging
- **Deployment** via Docker, systemd, or cloud services

But the architecture — the fundamental patterns — is the same.

---

**Ten modules. Ten concepts. One complete AI assistant.**

[<- README](./README.md)
