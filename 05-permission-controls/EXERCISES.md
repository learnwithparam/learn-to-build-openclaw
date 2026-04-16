# 05 Exercises — Permission Controls

## Exercise 1: Test the Three Tiers

**Goal**: Verify each safety tier works correctly.

1. Run the bot: `make 05-permission-controls`
2. Test a safe command: "Run `ls -la`" (should execute immediately)
3. Test a dangerous command: "Run `rm -rf /tmp/test`" or ask the bot to do something that would match a dangerous pattern
4. Test an unknown command: "Run `docker ps`" (should auto-approve)

**Checkpoint**: Safe commands run without hesitation. Dangerous patterns are blocked. Unknown commands get approved and saved.

---

## Exercise 2: Inspect exec-approvals.json

**Goal**: Understand persistent approvals.

1. After running a few commands, check `05-permission-controls/exec-approvals.json`
2. Verify it contains the commands that were auto-approved
3. Delete the file and try the same commands again — they should trigger approval again
4. Now add commands manually to the file and verify they're accepted without approval

**Checkpoint**: The approvals file is the persistent allowlist. Commands in it are always allowed.

---

## Exercise 3: Add Custom Safe Commands

**Goal**: Customize the safety model for your workflow.

1. Add new commands to `SAFE_COMMANDS`:
   ```python
   SAFE_COMMANDS = {
       ...,
       "docker", "git", "make", "cargo", "go",
   }
   ```
2. Add a new dangerous pattern:
   ```python
   DANGEROUS_PATTERNS = [
       ...,
       r"\bchmod\s+777\b",    # World-writable permissions
   ]
   ```
3. Test both additions.

**Checkpoint**: Your custom safe commands should run without approval. Your custom dangerous pattern should be blocked.

---

## Exercise 4: Design Telegram Approval UX

**Goal**: Think about how to make approvals user-friendly.

1. Sketch (on paper or in comments) how approval would work with Telegram inline keyboards:
   - What does the approval message look like?
   - What happens when the user clicks "Approve"?
   - What about "Always Allow"?
2. Consider: How would you handle the agent loop while waiting for approval? (The agent is blocked until the user responds.)
3. Bonus: Look up `telegram.InlineKeyboardButton` in the python-telegram-bot docs.

**Checkpoint**: You should understand that real approval UX requires async callbacks and a way to pause/resume the agent loop.
