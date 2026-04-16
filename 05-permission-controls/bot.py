#!/usr/bin/env python3
"""
05: Permission Controls — Three-tier command safety model.

Builds on 04 by adding:
  - SAFE_COMMANDS set (always allowed)
  - DANGEROUS_PATTERNS list (always blocked)
  - Persistent approval file (exec-approvals.json)
  - check_command_safety() with three-tier logic

Usage:
    uv run python 05-permission-controls/bot.py
"""
import json
import os
import re
import subprocess
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

load_dotenv(override=True)

MODEL = "claude-sonnet-4-20250514"
client = Anthropic()

BOT_DIR = Path(__file__).parent
SESSIONS_DIR = BOT_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

SOUL = (BOT_DIR.parent / "03-personality-soul" / "SOUL.md").read_text()

# --- Permission system ---

SAFE_COMMANDS = {
    "ls", "cat", "head", "tail", "wc", "grep", "find", "echo",
    "pwd", "whoami", "date", "cal", "uname", "which", "file",
    "python", "python3", "node", "pip", "npm",
}

DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\s+/",        # rm -rf /
    r"\bmkfs\b",              # Format filesystem
    r"\bdd\s+if=",            # Raw disk write
    r">\s*/dev/sd",           # Write to disk device
    r"\bshutdown\b",          # Shutdown system
    r"\breboot\b",            # Reboot system
    r"\bcurl\b.*\|\s*bash",   # Pipe curl to bash
    r"\bwget\b.*\|\s*bash",   # Pipe wget to bash
]

APPROVALS_FILE = BOT_DIR / "exec-approvals.json"


def load_approvals() -> set:
    """Load previously approved commands."""
    if APPROVALS_FILE.exists():
        return set(json.loads(APPROVALS_FILE.read_text()))
    return set()


def save_approval(command: str):
    """Save a command to the approved list."""
    approvals = load_approvals()
    approvals.add(command)
    APPROVALS_FILE.write_text(json.dumps(sorted(approvals), indent=2))


def check_command_safety(command: str) -> str:
    """
    Three-tier safety check:
      1. BLOCKED — matches dangerous patterns -> always reject
      2. SAFE — first word is in SAFE_COMMANDS -> always allow
      3. NEEDS_APPROVAL — check persistent approvals, else request approval
    Returns: "safe", "blocked", "approved", or "needs_approval"
    """
    # Tier 1: Check dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            return "blocked"

    # Tier 2: Check safe commands
    first_word = command.strip().split()[0] if command.strip() else ""
    if first_word in SAFE_COMMANDS:
        return "safe"

    # Tier 3: Check persistent approvals
    if command in load_approvals():
        return "approved"

    return "needs_approval"


# --- Tool definitions ---

TOOLS = [
    {
        "name": "run_command",
        "description": "Run a shell command. Subject to safety checks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to execute"}
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to read"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file, creating directories as needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to write to"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "web_search",
        "description": "Search the web (placeholder).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"],
        },
    },
]


def execute_tool(name: str, input: dict) -> str:
    """Execute a tool with permission checks for run_command."""
    if name == "run_command":
        command = input["command"]
        safety = check_command_safety(command)

        if safety == "blocked":
            return f"BLOCKED: Command '{command}' matches a dangerous pattern and cannot be executed."

        if safety == "needs_approval":
            # In a real Telegram bot, you'd use inline keyboards for approval.
            # For this workshop, we auto-approve and save for next time.
            save_approval(command)
            print(f"  [permission] Auto-approved: {command}")

        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30,
            )
            output = result.stdout + result.stderr
            return output[:10000] or "Command completed with no output."
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 30 seconds."
        except Exception as e:
            return f"Error: {e}"

    elif name == "read_file":
        try:
            return Path(input["path"]).read_text()[:10000]
        except Exception as e:
            return f"Error reading file: {e}"

    elif name == "write_file":
        try:
            path = Path(input["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(input["content"])
            return f"Wrote {len(input['content'])} chars to {input['path']}"
        except Exception as e:
            return f"Error writing file: {e}"

    elif name == "web_search":
        return f"[Web search placeholder] Query: {input['query']}"

    return f"Unknown tool: {name}"


# --- Session persistence ---

def load_session(user_id: str) -> list[dict]:
    path = SESSIONS_DIR / f"{user_id}.jsonl"
    if not path.exists():
        return []
    messages = []
    for line in path.read_text().splitlines():
        if line.strip():
            messages.append(json.loads(line))
    return messages


def save_session(user_id: str, messages: list[dict]):
    path = SESSIONS_DIR / f"{user_id}.jsonl"
    with open(path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")


# --- Agent loop ---

def run_agent_turn(user_id: str, user_text: str) -> str:
    """Run the agent loop with permission-checked tool execution."""
    messages = load_session(user_id)
    messages.append({"role": "user", "content": user_text})

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SOUL,
            tools=TOOLS,
            messages=messages,
        )

        assistant_content = []
        for block in response.content:
            if hasattr(block, "text"):
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        messages.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason != "tool_use":
            save_session(user_id, messages)
            text_parts = [b.text for b in response.content if hasattr(b, "text")]
            return "\n".join(text_parts) or "Done."

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"  [tool] {block.name}({json.dumps(block.input)[:100]})")
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        messages.append({"role": "user", "content": tool_results})


# --- Bot handler ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_text = update.message.text

    await update.message.reply_text("Working on it...")
    reply = run_agent_turn(user_id, user_text)
    await update.message.reply_text(reply[:4096])


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Agent bot is running with permission controls!")
    app.run_polling()


if __name__ == "__main__":
    main()
