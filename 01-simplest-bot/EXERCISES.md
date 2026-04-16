# 01 Exercises — The Simplest Bot

## Exercise 1: Read the Code

**Goal**: Understand every line of the bot.

1. Open `bot.py` and identify:
   - Where is the **Anthropic API call**?
   - Where is the **Telegram message handler**?
   - Where does the **response get sent back**?
2. Write down in your own words: what does each section do?

**Checkpoint**: You should be able to trace the flow: Telegram message -> API call -> reply.

---

## Exercise 2: Test Statelessness

**Goal**: Prove that the bot has no memory.

1. Run the bot: `make 01-simplest-bot`
2. Send these messages in order:
   ```
   My name is Alice and I love Python.
   What's my name?
   What programming language do I like?
   ```
3. Observe: Does the bot remember your name? Your language preference?

**Checkpoint**: The bot should fail to remember anything from previous messages — each message is independent.

---

## Exercise 3: Experiment with Prompts

**Goal**: Understand what the model can and can't do without history.

1. Try different types of prompts:
   ```
   Explain recursion in 3 sentences.
   Write a Python function to reverse a string.
   What's the capital of France?
   ```
2. Now try prompts that require context:
   ```
   Can you make it shorter?
   What about the second one?
   Add error handling to that.
   ```
3. Note which prompts work well and which fail.

**Checkpoint**: Single-turn factual and generative prompts work fine. Follow-up prompts fail because there's no history.

---

## Exercise 4: Identify the Limitation

**Goal**: Think about what's needed for a real assistant.

1. List 3 things a real AI assistant needs that this bot lacks.
2. For each, think about where that data would come from.
3. Sketch (on paper or in a comment) how you'd add conversation history.

**Checkpoint**: You should realize that the core missing piece is a `messages` list that persists across calls — which is exactly what module 02 adds.
