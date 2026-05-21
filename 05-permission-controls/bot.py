#!/usr/bin/env python3
"""
05: Permission Controls — Three-tier command safety model.

Builds on 04 by adding:
  - SAFE_COMMANDS set (always allowed)
  - DANGEROUS_PATTERNS list (always blocked)
  - Persistent approval file (exec-approvals.json)
  - check_command_safety() with three-tier logic

Usage:
    uv run python 05-permission-controls/bot.py            # CLI mode
    uv run python 05-permission-controls/bot.py --telegram # Telegram mode
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

load_dotenv(override=True)

MODEL = os.environ.get("OPENROUTER_MODEL", "qwen/qwen3-coder")
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

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
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            return "blocked"

    first_word = command.strip().split()[0] if command.strip() else ""
    if first_word in SAFE_COMMANDS:
        return "safe"

    if command in load_approvals():
        return "approved"

    return "needs_approval"


# --- Tool definitions (OpenAI format) ---

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command. Subject to safety checks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute"}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file, creating directories as needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to write to"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web (placeholder).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
            },
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    """Execute a tool with permission checks for run_command."""
    if name == "run_command":
        command = args["command"]
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
            return Path(args["path"]).read_text()[:10000]
        except Exception as e:
            return f"Error reading file: {e}"

    elif name == "write_file":
        try:
            path = Path(args["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args["content"])
            return f"Wrote {len(args['content'])} chars to {args['path']}"
        except Exception as e:
            return f"Error writing file: {e}"

    elif name == "web_search":
        return f"[Web search placeholder] Query: {args['query']}"

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
    history = load_session(user_id)
    history.append({"role": "user", "content": user_text})

    while True:
        messages = [{"role": "system", "content": SOUL}] + history

        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=4096,
            tools=TOOLS,
            messages=messages,
        )

        msg = response.choices[0].message

        assistant_msg = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        history.append(assistant_msg)

        if not msg.tool_calls:
            save_session(user_id, history)
            return msg.content or "Done."

        for tc in msg.tool_calls:
            try:
                tool_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                tool_args = {}
            print(f"  [tool] {tc.function.name}({json.dumps(tool_args)[:100]})")
            result = execute_tool(tc.function.name, tool_args)
            history.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })


# --- Telegram channel ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_text = update.message.text
    await update.message.reply_text("Working on it...")
    reply = run_agent_turn(user_id, user_text)
    await update.message.reply_text(reply[:4096])


def run_telegram():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print(f"Agent bot running with permission controls — model: {MODEL}")
    app.run_polling()


# --- CLI channel ---

def run_cli():
    user_id = "cli-user"
    print(f"OpenClaw CLI (permissioned tools) — model: {MODEL}. Type 'exit' to quit.\n")
    while True:
        try:
            user_text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user_text in {"exit", "quit"}:
            break
        if not user_text:
            continue
        reply = run_agent_turn(user_id, user_text)
        print(f"bot> {reply}\n")


def main():
    if "--telegram" in sys.argv:
        run_telegram()
    else:
        run_cli()


if __name__ == "__main__":
    main()
