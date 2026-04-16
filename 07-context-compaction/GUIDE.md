# 07 Guide: Context Compaction

## The Context Window Problem

Every LLM has a context window — the maximum number of tokens it can process in a single call. For Claude Sonnet, this is ~200K tokens. Sounds like a lot, but with tool calls (which include full file contents, command output, etc.), it fills up fast.

When you exceed the limit, the API returns an error. The bot crashes. The conversation is dead.

## The Compaction Strategy

```
Before compaction:
  [msg 1] [msg 2] [msg 3] ... [msg 97] [msg 98] [msg 99] [msg 100]
   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   Old messages (summarize these)         Recent messages (keep verbatim)

After compaction:
  [summary of msgs 1-90] [msg 91] [msg 92] ... [msg 100]
```

The strategy:
1. **Estimate** total tokens in the session
2. If above threshold, **split** into old and recent
3. **Summarize** old messages using Claude
4. **Merge** summary + recent messages
5. **Save** the compacted session

## Token Estimation

```python
def estimate_tokens(messages):
    total_chars = sum(len(json.dumps(msg)) for msg in messages)
    return total_chars // 4
```

Why `chars / 4`? English text averages ~4 characters per token. This is a rough heuristic — not exact, but good enough for triggering compaction. You don't need precision here; you just need to know "are we getting close to the limit?"

## What Gets Preserved

The summarization prompt asks Claude to preserve:
- **Key facts** (names, preferences, decisions)
- **Important context** (what was discussed, what was decided)
- **Recent actions** (what tools were used, what happened)

What typically gets lost:
- Exact wording of old messages
- Detailed tool output from early in the conversation
- The "flavor" of the conversation

## Why SOUL Survives

Remember from module 03: the SOUL is passed as the `system` parameter, not in the `messages` array. Compaction only affects messages. The bot's identity is always intact.

## When Compaction Triggers

```python
tokens = estimate_tokens(messages)
if tokens > TOKEN_THRESHOLD:
    messages = compact_session(messages)
```

Compaction happens at the start of each `run_agent_turn()`, before calling the API. This ensures we never send a request that exceeds the context window.

## Compaction Quality

The quality of compaction depends on the summarization prompt. Better prompts = better preservation of key information. You can experiment with:
- "Preserve all proper nouns and numbers"
- "Keep a bulleted list of key facts"
- "Maintain the chronological order of events"

---

**The context window is finite. Compaction makes conversations infinite.**

[<- README](./README.md) | [Next: Long-Term Memory ->](../08-long-term-memory/GUIDE.md)
