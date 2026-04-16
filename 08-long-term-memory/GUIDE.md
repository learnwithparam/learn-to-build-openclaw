# 08 Guide: Long-Term Memory

## Session vs Memory

These are two different systems with different purposes:

| Aspect | Session | Memory |
|--------|---------|--------|
| Stores | Conversation history | Facts and knowledge |
| Lifetime | One conversation (or until compaction) | Forever |
| Format | JSONL (messages) | Markdown (facts) |
| Access | Automatic (loaded every turn) | On-demand (via tools) |
| Scope | Per-user | Shared (could be per-user) |

A session is like short-term memory — it remembers what was said. Memory is like a notebook — it remembers what was learned.

## File-Based Memory Storage

Memories are stored as markdown files in `./memory/`:

```
memory/
    user-preferences.md
    project-details.md
    technical-notes.md
```

Each file can contain multiple entries:

```markdown
## User Preferences (2024-01-15 10:30)
Prefers Python over JavaScript. Uses VS Code.

## User Preferences (2024-01-16 14:20)
Favorite framework is FastAPI. Dislikes ORMs.
```

Why markdown?
- **Human-readable** — You can inspect memories directly
- **Append-friendly** — New memories are appended, not overwritten
- **Topic-organized** — File names group related memories
- **Git-friendly** — Easy to track changes over time

## Keyword Search

```python
def memory_search(query):
    query_words = query.lower().split()
    results = []
    for filepath in MEMORY_DIR.glob("*.md"):
        text = filepath.read_text()
        matches = sum(1 for word in query_words if word in text.lower())
        if matches > 0:
            results.append((matches, filepath.stem, text[:500]))
    results.sort(reverse=True)
    return format_results(results[:5])
```

This is deliberately simple — just counting keyword matches. It works surprisingly well for small memory stores. For larger systems, you'd want:
- **Embeddings** — Vector similarity for semantic search
- **Full-text search** — Libraries like Whoosh or SQLite FTS
- **Structured storage** — JSON or database for queryable facts

## Proactive Memory in the SOUL

The SOUL instructs the agent to use memory proactively:

```markdown
## Memory Strategy
- When the user shares important facts, proactively use save_memory
- Before answering questions about the user, check memory_search first
- Save memories with descriptive topics for easy retrieval
```

This is key: the agent doesn't just wait to be told to remember things. It recognizes important information and saves it automatically.

## The Memory Lifecycle

```
User says "I work at Acme Corp on the Rocket project"
    |
    v
Agent recognizes this as important → save_memory("user-work", "Works at Acme Corp on Rocket project")
    |
    v
Memory saved to memory/user-work.md
    |
    ... (days later, new session) ...
    |
User asks "What project am I working on?"
    |
    v
Agent calls memory_search("project work") → finds user-work.md
    |
    v
Agent responds: "You're working on the Rocket project at Acme Corp."
```

---

**Sessions are temporary. Memory is permanent. Together, they make a real assistant.**

[<- README](./README.md) | [Next: Concurrency & Scheduling ->](../09-concurrency-scheduling/GUIDE.md)
