# Learn to Build OpenClaw

Learn how persistent AI assistants work by rebuilding OpenClaw from first principles — starting with a tiny bot and incrementally adding sessions, personality, tools, permissions, a multi-channel gateway, context compaction, memory, scheduling, and multi-agent routing.

The workshop runs on **OpenRouter** (default model: [`qwen/qwen3-coder`](https://openrouter.ai/qwen/qwen3-coder)) so you get cheap, accurate coding-model output without locking the workshop to any single provider. Swap `OPENROUTER_MODEL` to try DeepSeek, Haiku, or any other OpenRouter model.

Every module ships with two ways to run it:
- **CLI mode** (default) — a terminal REPL. No Telegram setup needed.
- **Telegram mode** — pass `--telegram` to run as a real Telegram bot.

Based on [Nader Dabit's blog post](https://www.nader.fyi/building-openclaw-personal-ai-assistant) on building a personal AI assistant.

## Workshop Modules

| # | Module | Core Addition | Key Insight | Lines |
|---|--------|---------------|-------------|-------|
| 01 | [Simplest Bot](./01-simplest-bot/) | OpenRouter call + CLI/Telegram channel | An AI bot is just an API call wrapped in a message handler | ~50 |
| 02 | [Persistent Sessions](./02-persistent-sessions/) | JSONL per-user storage | JSONL is the simplest crash-safe persistence format | ~80 |
| 03 | [Personality & Soul](./03-personality-soul/) | System prompt + SOUL.md | The system prompt IS the agent's identity | ~90 |
| 04 | [Tools & Agent Loop](./04-tools-agent-loop/) | 4 tools + agent loop | The agent loop turns a chatbot into an agent | ~200 |
| 05 | [Permission Controls](./05-permission-controls/) | Three-tier safety model | Safety is a persistent allowlist, not a per-request prompt | ~250 |
| 06 | [Gateway](./06-gateway/) | HTTP + Telegram channels | The agent logic is channel-agnostic | ~300 |
| 07 | [Context Compaction](./07-context-compaction/) | Token mgmt + summarization | Summarize the old, keep the recent, never hit the limit | ~350 |
| 08 | [Long-Term Memory](./08-long-term-memory/) | File-based memory + search | Sessions remember conversations. Memory remembers knowledge | ~400 |
| 09 | [Concurrency & Scheduling](./09-concurrency-scheduling/) | Locks + cron tasks | Lock per session, schedule per task — the agent never sleeps | ~450 |
| 10 | [Multi-Agent Integration](./10-multi-agent-integration/) | Agent routing + full system | Specialize agents, share memory — that's collaboration | ~400 |

### What You'll Learn

- **The Bot Pattern** — How to wire an LLM to a messaging platform
- **Session Persistence** — Crash-safe conversation storage with JSONL
- **Agent Identity** — Designing personality and boundaries with system prompts
- **Tool Use & Agent Loops** — Giving an AI real-world capabilities
- **Safety & Permissions** — Building a three-tier command safety model
- **Multi-Channel Architecture** — Decoupling agent logic from delivery channels
- **Context Management** — Automatic summarization when context grows too large
- **Long-Term Memory** — Persistent knowledge that survives session resets
- **Concurrency** — Per-session locking and scheduled background tasks
- **Multi-Agent Systems** — Specialized agents with shared memory

## Getting Started

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- An [OpenRouter API key](https://openrouter.ai/keys) — credits start at $1; `qwen/qwen3-coder` is one of the cheapest capable coding models on the platform
- *(Optional)* a [Telegram Bot Token](https://core.telegram.org/bots#how-do-i-create-a-bot) only if you want to run modules in `--telegram` mode

### Setup

1.  **Install dependencies**:
    ```bash
    make install
    ```

2.  **Configure environment**:
    ```bash
    cp .env.example .env
    # Edit .env and add your OPENROUTER_API_KEY
    # (TELEGRAM_BOT_TOKEN only needed for --telegram mode)
    ```

3.  **Run the first bot in CLI mode**:
    ```bash
    make 01-simplest-bot
    ```

### Running Each Module

```bash
make 01-simplest-bot          # Start here! 20-line bot
make 02-persistent-sessions   # + JSONL session storage
make 03-personality-soul      # + SOUL.md system prompt
make 04-tools-agent-loop      # + Tools and agent loop
make 05-permission-controls   # + Three-tier safety model
make 06-gateway               # + HTTP gateway alongside Telegram
make 07-context-compaction    # + Automatic context summarization
make 08-long-term-memory      # + File-based persistent memory
make 09-concurrency-scheduling # + Per-session locks and cron
make 10-multi-agent-integration # + Multi-agent routing
```

## Learning Path

```
Start Here
    |
    v
01 [Simplest Bot] ───────────> "An API call in a message handler"
    |                            ~20 lines, stateless
    v
02 [Persistent Sessions] ────> "JSONL is crash-safe persistence"
    |                            ~80 lines, multi-turn memory
    v
03 [Personality & Soul] ─────> "The system prompt IS identity"
    |                            ~90 lines, + SOUL.md
    v
04 [Tools & Agent Loop] ─────> "The loop makes it an agent"
    |                            ~200 lines, 4 tools
    v
05 [Permission Controls] ────> "Safety as persistent allowlist"
    |                            ~250 lines, 3-tier model
    v
06 [Gateway] ────────────────> "Agent logic is channel-agnostic"
    |                            ~300 lines, HTTP + Telegram
    v
07 [Context Compaction] ─────> "Summarize old, keep recent"
    |                            ~350 lines, token management
    v
08 [Long-Term Memory] ───────> "Memory outlives sessions"
    |                            ~400 lines, file-based search
    v
09 [Concurrency & Scheduling] > "Lock per session, schedule per task"
    |                            ~450 lines, threading + cron
    v
10 [Multi-Agent Integration] ─> "Specialize and collaborate"
                                  ~400 lines, routing + full system
```

**Recommended approach:**
1. Read and run 01 first — understand the simplest possible bot
2. Compare 01 -> 02 — see how session persistence works
3. Study 03 for identity design patterns
4. Master 04 for the agent loop — this is the biggest jump
5. Explore 05-06 for safety and architecture
6. Study 07-08 for context and memory management
7. Explore 09-10 for production concerns and multi-agent systems

## Each Module Includes

| File | Purpose |
|------|---------|
| `bot.py` | The runnable bot code (or `mini-openclaw.py` in module 10) |
| `README.md` | Module intro, learning goals, how to run |
| `GUIDE.md` | Deep-dive explanation of concepts |
| `EXERCISES.md` | 3-4 hands-on exercises |

## The Core Pattern

Every persistent AI assistant is built on this foundation:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

def handle_message(user_id, text):
    history = load_session(user_id)
    history.append({"role": "user", "content": text})

    messages = [{"role": "system", "content": SOUL}] + history
    response = client.chat.completions.create(
        model=os.environ.get("OPENROUTER_MODEL", "qwen/qwen3-coder"),
        messages=messages,
    )

    reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply})
    save_session(user_id, history)
    return reply
```

Load history, call the API, save the response. Everything else is refinement. The OpenRouter base URL means you can swap the model line and target any provider on the platform (qwen, deepseek, claude, gpt, gemini, ...).

## Verifying Your Setup

```bash
make test    # Runs automated checks on all modules
```
