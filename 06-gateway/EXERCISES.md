# 06 Exercises — Gateway

## Exercise 1: Cross-Channel Conversation

**Goal**: Prove that sessions are shared across channels.

1. Run the bot: `make 06-gateway`
2. Send a message via Telegram: "My name is Alice"
3. Find your Telegram user ID in the console output
4. Send via HTTP with the same user ID:
   ```bash
   curl -X POST http://localhost:5000/chat \
     -H 'Content-Type: application/json' \
     -d '{"user_id": "YOUR_TELEGRAM_ID", "message": "What is my name?"}'
   ```
5. Verify the HTTP response recalls your name from the Telegram conversation

**Checkpoint**: The HTTP endpoint should know your name because it shares the session file.

---

## Exercise 2: Test HTTP Endpoint

**Goal**: Understand the HTTP API.

1. Test the health endpoint: `curl http://localhost:5000/health`
2. Send a chat message:
   ```bash
   curl -X POST http://localhost:5000/chat \
     -H 'Content-Type: application/json' \
     -d '{"user_id": "http-test", "message": "What can you do?"}'
   ```
3. Send a follow-up with the same user_id and verify context is maintained
4. Try with a different user_id — verify it's a fresh conversation

**Checkpoint**: Each user_id gets its own session. The HTTP API is a complete chat interface.

---

## Exercise 3: Add a CLI REPL Channel

**Goal**: Add a third interface to the gateway.

1. Add a CLI REPL function:
   ```python
   def start_cli():
       user_id = "cli-user"
       print("CLI mode. Type 'q' to quit.")
       while True:
           text = input(">> ")
           if text.lower() in ("q", "quit", "exit"):
               break
           reply = run_agent_turn(user_id, text)
           print(reply)
   ```
2. Add it as another option (e.g., check a `--cli` flag in `main()`)
3. Test it alongside the other channels

**Checkpoint**: You should be able to chat via CLI, Telegram, and HTTP — all sharing sessions by user_id.

---

## Exercise 4: Design a Channel Adapter Interface

**Goal**: Think about how to make adding channels systematic.

1. What do all channels have in common? (hint: extract user_id, extract text, call agent, send reply)
2. Design a simple interface (class or protocol) that all channel adapters would implement
3. Consider: How would you add Slack, Discord, or WhatsApp as channels?

**Checkpoint**: You should see that the gateway pattern reduces each new channel to ~20 lines of adapter code.
