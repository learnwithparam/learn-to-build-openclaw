# 03 Guide: Personality & Soul

## System Prompt vs First Message

The Anthropic API has a dedicated `system` parameter, separate from the `messages` array. This matters:

```python
# System prompt — shapes ALL responses
response = client.messages.create(
    system=SOUL,          # <-- Always present, never in history
    messages=messages,     # <-- User/assistant turns only
)
```

The system prompt:
- Is always "above" the conversation — the model sees it first
- Never appears in the message history
- Survives session resets and context compaction (module 07)
- Applies equally to all users

## Why SOUL Survives Compaction

When a conversation gets too long (module 07), we'll summarize old messages. But the system prompt is never part of the messages array — it's a separate parameter. This means the bot's identity is never summarized away or lost.

This is why we put identity in `system` rather than as the first user/assistant message.

## Designing a Good SOUL.md

A good SOUL has four sections:

1. **Identity** — Who is the agent? What's its name?
2. **Personality** — How does it communicate? What's its tone?
3. **Boundaries** — What should it refuse or avoid?
4. **Memory Strategy** — How should it handle information the user shares?

```markdown
# OpenClaw

## Personality
- Helpful, concise, technically competent

## Boundaries
- Don't pretend to browse the internet
- Don't make up information

## Memory Strategy
- Pay attention to user-shared facts
- Reference previous context naturally
```

## The SOUL.md Pattern

Why a separate file instead of a string in code?

1. **Non-engineers can edit it** — Product managers, designers can tweak personality
2. **Version control** — You can track personality changes over time
3. **Hot-reload potential** — In production, you could reload SOUL.md without restarting
4. **Experimentation** — Easy to A/B test different personalities

This is the same pattern used by OpenClaw, Claude Code (CLAUDE.md), and other production AI assistants.

## What Changes from Module 02

Only two lines of code changed:

```python
# New: Load the SOUL file
SOUL = (BOT_DIR / "SOUL.md").read_text()

# Changed: Add system parameter
response = client.messages.create(
    model=MODEL,
    max_tokens=1024,
    system=SOUL,       # <-- This is new
    messages=messages,
)
```

The entire personality system is just loading a text file and passing it as a parameter. The simplicity is the point.

---

**Identity is just a text file. The system prompt makes it real.**

[<- README](./README.md) | [Next: Tools & Agent Loop ->](../04-tools-agent-loop/GUIDE.md)
