#!/usr/bin/env python3
"""
06: Gateway — Channel-agnostic agent with HTTP + Telegram.

Builds on 05 by adding:
  - Flask HTTP endpoint (/chat) alongside Telegram
  - Both channels call the same run_agent_turn()
  - Sessions keyed by user_id (shared across channels)
  - Threading for concurrent channel operation

Usage:
    uv run python 06-gateway/bot.py
"""
import json
import os
import re
import subprocess
import threading
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

load_dotenv(override=True)

MODEL = "claude-sonnet-4-20250514"
client = Anthropic()

BOT_DIR = Path(__file__).parent
SESSIONS_DIR = BOT_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

SOUL = (BOT_DIR.parent / "03-personality-soul" / "SOUL.md").read_text()

# --- Permission system (from module 05) ---

SAFE_COMMANDS = {
    "ls", "cat", "head", "tail", "wc", "grep", "find", "echo",
    "pwd", "whoami", "date", "cal", "uname", "which", "file",
    "python", "python3", "node", "pip", "npm",
}

DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\s+/",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r">\s*/dev/sd",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bcurl\b.*\|\s*bash",
    r"\bwget\b.*\|\s*bash",
]

APPROVALS_FILE = BOT_DIR / "exec-approvals.json"


def load_approvals() -> set:
    if APPROVALS_FILE.exists():
        return set(json.loads(APPROVALS_FILE.read_text()))
    return set()


def save_approval(command: str):
    approvals = load_approvals()
    approvals.add(command)
    APPROVALS_FILE.write_text(json.dumps(sorted(approvals), indent=2))


def check_command_safety(command: str) -> str:
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            return "blocked"
    first_word = command.strip().split()[0] if command.strip() else ""
    if first_word in SAFE_COMMANDS:
        return "safe"
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
    if name == "run_command":
        command = input["command"]
        safety = check_command_safety(command)
        if safety == "blocked":
            return f"BLOCKED: Command '{command}' matches a dangerous pattern."
        if safety == "needs_approval":
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


# --- Agent loop (channel-agnostic) ---

def run_agent_turn(user_id: str, user_text: str) -> str:
    """The core agent — same function called by both Telegram and HTTP."""
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


# --- Channel 1: Telegram ---

async def handle_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_text = update.message.text
    print(f"  [telegram] User {user_id}: {user_text[:50]}")

    await update.message.reply_text("Working on it...")
    reply = run_agent_turn(user_id, user_text)
    await update.message.reply_text(reply[:4096])


def start_telegram():
    """Start Telegram bot in a separate thread."""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram))
    print("[telegram] Bot is running!")
    app.run_polling()


# --- Channel 2: HTTP (Flask) ---

flask_app = Flask(__name__)


@flask_app.route("/chat", methods=["POST"])
def http_chat():
    """HTTP endpoint: POST /chat with {"user_id": "...", "message": "..."}"""
    data = request.get_json()
    user_id = data.get("user_id", "http-user")
    message = data.get("message", "")
    print(f"  [http] User {user_id}: {message[:50]}")

    reply = run_agent_turn(user_id, message)
    return jsonify({"reply": reply})


@flask_app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


def start_http():
    """Start Flask server in a separate thread."""
    print("[http] Server running on http://localhost:5000")
    flask_app.run(host="0.0.0.0", port=5000, debug=False)


# --- Main: start both channels ---

def main():
    print("Starting gateway with Telegram + HTTP channels...")
    print("  Telegram: Send messages to your bot")
    print("  HTTP: curl -X POST http://localhost:5000/chat -H 'Content-Type: application/json' -d '{\"user_id\": \"test\", \"message\": \"hello\"}'")

    # Start HTTP in a daemon thread
    http_thread = threading.Thread(target=start_http, daemon=True)
    http_thread.start()

    # Start Telegram in the main thread (it has its own event loop)
    start_telegram()


if __name__ == "__main__":
    main()
