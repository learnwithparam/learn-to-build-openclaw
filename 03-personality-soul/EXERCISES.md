# 03 Exercises — Personality & Soul

## Exercise 1: Test the Default SOUL

**Goal**: See how SOUL.md shapes the bot's behavior.

1. Run the bot: `make 03-personality-soul`
2. Try these prompts and observe how the bot responds:
   ```
   Who are you?
   Tell me a joke.
   Can you browse the internet for me?
   ```
3. Compare the responses to module 02 — is the personality consistent?

**Checkpoint**: The bot should identify itself according to SOUL.md and respect its boundaries.

---

## Exercise 2: Write a Custom SOUL

**Goal**: Experience how changing the system prompt changes behavior.

1. Edit `03-personality-soul/SOUL.md` to create a different personality. Try one of these:
   - A pirate AI that talks like a pirate while being helpful
   - A Socratic tutor that answers questions with more questions
   - A terse Unix wizard that gives minimal, command-line-focused answers
2. Restart the bot and test the new personality
3. Try the same prompts from Exercise 1 — how do responses differ?

**Checkpoint**: Same code, different SOUL.md = completely different behavior.

---

## Exercise 3: Test Boundary Design

**Goal**: Understand how boundaries shape what the bot will and won't do.

1. Add specific boundaries to SOUL.md:
   ```markdown
   ## Boundaries
   - Never write code in JavaScript — always suggest Python instead
   - Always ask clarifying questions before giving advice
   - Refuse to discuss topics outside of programming
   ```
2. Restart and test:
   ```
   Write me a React component.
   What's the best restaurant in NYC?
   Help me write a sorting algorithm.
   ```
3. Does the bot respect your boundaries consistently?

**Checkpoint**: Well-written boundaries are usually respected. Vague boundaries are sometimes ignored. Specificity matters.

---

## Exercise 4: SOUL Persistence Experiment

**Goal**: Understand that SOUL is separate from session history.

1. Delete the session files in `03-personality-soul/sessions/`
2. Restart the bot and chat — the personality should be unchanged
3. Now temporarily rename SOUL.md to SOUL.md.bak and restart — what happens?

**Checkpoint**: Sessions store conversation history. SOUL stores identity. They're independent — deleting sessions doesn't change personality, and vice versa.
