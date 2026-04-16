# 09 Exercises — Concurrency & Scheduling

## Exercise 1: Test Concurrent Access

**Goal**: Verify per-session locking works.

1. Run the bot: `make 09-concurrency-scheduling`
2. Quickly send multiple messages via both channels:
   ```bash
   # Terminal 1: Rapid HTTP requests
   for i in 1 2 3 4 5; do
     curl -s -X POST http://localhost:5000/chat \
       -H 'Content-Type: application/json' \
       -d "{\"user_id\": \"test\", \"message\": \"Message $i\"}" &
   done
   ```
3. Watch the console — you should see messages being processed sequentially for the same user_id
4. Send messages for different user_ids in parallel — they should process concurrently

**Checkpoint**: Same-user messages are serialized (no interleaving). Different-user messages run in parallel.

---

## Exercise 2: Trigger the Heartbeat

**Goal**: See a scheduled task in action.

1. In `bot.py`, change the heartbeat frequency for testing:
   ```python
   schedule.every(1).minutes.do(heartbeat_task)
   ```
2. Run the bot and wait for the `[cron]` log message
3. Inspect the cron session file: `cat 09-concurrency-scheduling/sessions/cron:daily-summary.jsonl`
4. Verify it's a separate conversation from your user sessions

**Checkpoint**: The heartbeat should run automatically and create its own isolated session file.

---

## Exercise 3: Add a Custom Scheduled Task

**Goal**: Create your own cron job.

1. Add a new task function:
   ```python
   def memory_cleanup_task():
       user_id = "cron:memory-cleanup"
       run_agent_turn(user_id, "List all memory files and their sizes. Report any that are larger than 1KB.")
   ```
2. Schedule it: `schedule.every(6).hours.do(memory_cleanup_task)`
3. Test it by running it manually: call `memory_cleanup_task()` from the startup code
4. Check the cron session file

**Checkpoint**: Your custom task should create its own session and execute independently.

---

## Exercise 4: Design a Notification System

**Goal**: Think about how to deliver scheduled task results to users.

1. Currently, cron tasks write to their own sessions but don't notify users
2. Design a notification system:
   - Where would notifications be stored? (A notification queue? A file per user?)
   - How would the Telegram handler check for pending notifications?
   - Should notifications be pushed (proactive) or pulled (on next message)?
3. Consider: What if a cron task discovers something urgent? How do you notify the user immediately via Telegram?

**Checkpoint**: You should understand that connecting cron results to user notifications requires a message queue or callback mechanism.
