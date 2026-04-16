# 08 Exercises — Long-Term Memory

## Exercise 1: Test Proactive Memory Saving

**Goal**: See the agent save memories automatically.

1. Run the bot: `make 08-long-term-memory`
2. Share some facts:
   ```
   My name is Alice and I'm a senior engineer at Acme Corp.
   I'm working on a project called Rocket using Python and FastAPI.
   My favorite editor is Neovim and I prefer dark themes.
   ```
3. Check the console output for `save_memory` tool calls
4. Inspect the `08-long-term-memory/memory/` directory

**Checkpoint**: The agent should proactively save these facts without being asked. You should see markdown files in the memory directory.

---

## Exercise 2: Cross-Session Recall

**Goal**: Prove that memory outlives sessions.

1. After Exercise 1, delete the session file:
   ```bash
   rm 08-long-term-memory/sessions/*.jsonl
   ```
2. Restart the bot
3. Ask:
   ```
   What do you know about me?
   What project am I working on?
   ```

**Checkpoint**: The session is gone, but the agent should recall your facts from memory files. This is the key difference between sessions and memory.

---

## Exercise 3: Inspect Memory Files

**Goal**: Understand the memory storage format.

1. After Exercises 1-2, look at the files in `08-long-term-memory/memory/`
2. Open each `.md` file and observe:
   - The topic headers
   - The timestamps
   - How information is organized
3. Try manually editing a memory file (add a fact), then ask the bot about it

**Checkpoint**: Memory files are just markdown — human-readable and editable. The bot reads them on demand via `memory_search`.

---

## Exercise 4: Design a Memory Search Upgrade

**Goal**: Think about better retrieval mechanisms.

1. Consider the limitations of keyword search:
   - "What's my job?" won't match "works at Acme Corp as senior engineer"
   - Synonyms aren't handled
   - No semantic understanding
2. Research (or sketch) how you'd implement:
   - Embedding-based search using a library like `sentence-transformers`
   - SQLite full-text search (FTS5)
   - A hybrid approach (keyword + embedding)
3. What trade-offs does each approach have?

**Checkpoint**: You should understand that keyword search is simple but limited. Embeddings provide semantic matching but add complexity and dependencies.
