# 07 Exercises — Context Compaction

## Exercise 1: Trigger Compaction

**Goal**: See compaction in action.

1. In `bot.py`, temporarily lower the threshold:
   ```python
   TOKEN_THRESHOLD = 2000   # Very low — triggers quickly
   RECENT_KEEP = 4          # Keep only last 4 messages
   ```
2. Run the bot and have a conversation of ~10 messages
3. Watch the console for the `[compaction]` log message
4. Continue chatting — verify the bot still remembers key facts

**Checkpoint**: You should see compaction trigger and the bot should retain important information from the summarized portion.

---

## Exercise 2: Inspect Before and After

**Goal**: Understand what compaction does to session files.

1. With the low threshold from Exercise 1, chat until compaction triggers
2. Open the JSONL session file and look at the structure:
   - The first message should be `[Previous conversation summary follows]`
   - The second should contain the summary
   - The remaining should be verbatim recent messages
3. Compare the file size before and after compaction

**Checkpoint**: The session file should be much smaller after compaction, with old messages replaced by a concise summary.

---

## Exercise 3: Test Fact Preservation

**Goal**: Verify which facts survive compaction.

1. Start a fresh conversation and share specific facts:
   ```
   My name is Alice. I work at Acme Corp. My favorite language is Rust.
   I have a dog named Max. I live in San Francisco.
   ```
2. Continue chatting about other topics until compaction triggers
3. Then ask:
   ```
   What's my name? Where do I work? What's my dog's name?
   ```
4. Note which facts were preserved and which were lost

**Checkpoint**: Most key facts should survive compaction, though some details may be lost depending on the summarization quality.

---

## Exercise 4: Improve Summarization

**Goal**: Experiment with better summarization prompts.

1. Find the summarization prompt in `compact_session()`:
   ```python
   "Summarize this conversation history concisely, preserving key facts..."
   ```
2. Try different prompts:
   - "Create a structured summary with sections: Key Facts, Decisions Made, Open Topics"
   - "List every proper noun, number, and preference mentioned, then summarize the discussion"
3. Test each version with the same conversation and compare results

**Checkpoint**: More structured summarization prompts generally preserve more information but use more tokens.
