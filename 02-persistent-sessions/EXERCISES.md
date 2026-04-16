# 02 Exercises — Persistent Sessions

## Exercise 1: Test Multi-Turn Memory

**Goal**: Verify that the bot maintains conversation context.

1. Run the bot: `make 02-persistent-sessions`
2. Send these messages:
   ```
   My name is Alice and I'm a Python developer.
   What's my name?
   What language do I work with?
   ```
3. Verify the bot correctly recalls both facts.

**Checkpoint**: The bot should remember everything you've told it within the session.

---

## Exercise 2: Test Crash Recovery

**Goal**: Prove that sessions survive restarts.

1. With the bot running, send a few messages to establish context
2. Stop the bot with Ctrl+C
3. Restart it: `make 02-persistent-sessions`
4. Send "What have we talked about?" or "What's my name?"

**Checkpoint**: The bot should recall your previous conversation — the JSONL file persisted it.

---

## Exercise 3: Inspect the Session Files

**Goal**: Understand the JSONL format by reading raw session data.

1. After a conversation, look in the `02-persistent-sessions/sessions/` directory
2. Open a `.jsonl` file with `cat` or your editor
3. Verify:
   - Each line is valid JSON
   - Messages alternate between `"role": "user"` and `"role": "assistant"`
   - The content matches what you typed and received

**Checkpoint**: You should see the exact conversation history as alternating JSON lines.

---

## Exercise 4: Compare Persistence Approaches

**Goal**: Think critically about the tradeoffs of different storage formats.

1. Consider: What happens if you use a single `session.json` file instead of JSONL?
   - How would you append a message?
   - What happens if the bot crashes during a write?
2. Consider: What would change if you used SQLite instead?
   - What are the advantages?
   - What complexity does it add?
3. Write a short paragraph (in comments or notes) about when you'd choose each format.

**Checkpoint**: You should understand that JSONL's append-only nature makes it crash-safe, while JSON requires rewriting the entire file and SQLite adds complexity for simple use cases.
