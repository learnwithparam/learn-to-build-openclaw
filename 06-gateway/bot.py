#!/usr/bin/env python3
"""
06: Gateway — Channel-agnostic agent with HTTP + Telegram + CLI.

Builds on 05 by adding:
  - Flask HTTP endpoint (/chat) alongside Telegram
  - All channels call the same run_agent_turn()
  - Sessions keyed by user_id (shared across channels)
  - Threading for concurrent channel operation

Usage:
    uv run python 06-gateway/bot.py            # CLI only
    uv run python 06-gateway/bot.py --http     # CLI + HTTP server
    uv run python 06-gateway/bot.py --telegram # Telegram + HTTP (full gateway)
"""
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request, jsonify
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

# --- Permission system (from module 05) ---

SAFE_COMMANDS = {
    "ls", "cat", "head", "tail", "wc", "grep", "find", "echo",
    "pwd", "whoami", "date", "cal", "uname", "which", "file",
    "python", "python3", "node", "pip", "npm",
}

DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\s+/", r"\bmkfs\b", r"\bdd\s+if=",
    r">\s*/dev/sd", r"\bshutdown\b", r"\breboot\b",
    r"\bcurl\b.*\|\s*bash", r"\bwget\b.*\|\s*bash",
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


# --- Tool definitions (OpenAI format) ---

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command. Subject to safety checks.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "The shell command to execute"}},
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
                "properties": {"path": {"type": "string", "description": "Path to the file to read"}},
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
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    if name == "run_command":
        command = args["command"]
        safety = check_command_safety(command)
        if safety == "blocked":
            return f"BLOCKED: Command '{command}' matches a dangerous pattern."
        if safety == "needs_approval":
            save_approval(command)
            print(f"  [permission] Auto-approved: {command}")
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            return (result.stdout + result.stderr)[:10000] or "Command completed with no output."
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


# --- Agent loop (channel-agnostic) ---

def run_agent_turn(user_id: str, user_text: str) -> str:
    """The core agent — same function called by every channel."""
    history = load_session(user_id)
    history.append({"role": "user", "content": user_text})

    while True:
        messages = [{"role": "system", "content": SOUL}] + history
        response = client.chat.completions.create(
            model=MODEL, max_tokens=4096, tools=TOOLS, messages=messages,
        )
        msg = response.choices[0].message

        assistant_msg = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
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
            history.append({"role": "tool", "tool_call_id": tc.id, "content": result})


# --- Channel 1: Telegram ---

async def handle_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_text = update.message.text
    print(f"  [telegram] User {user_id}: {user_text[:50]}")
    await update.message.reply_text("Working on it...")
    reply = run_agent_turn(user_id, user_text)
    await update.message.reply_text(reply[:4096])


def start_telegram():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram))
    print("[telegram] Bot is running!")
    app.run_polling()


# --- Channel 2: HTTP (Flask) ---

flask_app = Flask(__name__)


@flask_app.route("/chat", methods=["POST"])
def http_chat():
    """POST /chat with {"user_id": "...", "message": "..."}"""
    data = request.get_json()
    user_id = data.get("user_id", "http-user")
    message = data.get("message", "")
    print(f"  [http] User {user_id}: {message[:50]}")
    reply = run_agent_turn(user_id, message)
    return jsonify({"reply": reply})


@flask_app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": MODEL})


def start_http():
    print("[http] Server running on http://localhost:5000")
    flask_app.run(host="0.0.0.0", port=5000, debug=False)


# --- Channel 3: CLI ---

def start_cli():
    user_id = "cli-user"
    print(f"[cli] OpenClaw — model: {MODEL}. Type 'exit' to quit.\n")
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


# --- Main: pick channels ---

def main():
    has_telegram = "--telegram" in sys.argv
    has_http = "--http" in sys.argv or has_telegram

    if has_http:
        threading.Thread(target=start_http, daemon=True).start()

    if has_telegram:
        start_telegram()
    else:
        start_cli()


if __name__ == "__main__":
    main()
