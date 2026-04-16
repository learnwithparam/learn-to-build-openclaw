#!/usr/bin/env python3
"""
07: Context Compaction — Automatic summarization when context grows too large.

Builds on 06 by adding:
  - estimate_tokens() — heuristic token counting (chars / 4)
  - compact_session() — split-summarize-merge strategy
  - Automatic compaction before API calls when threshold is exceeded

Usage:
    uv run python 07-context-compaction/bot.py
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

# Compaction settings
TOKEN_THRESHOLD = 50000   # Trigger compaction above this
RECENT_KEEP = 10          # Number of recent messages to keep verbatim


# --- Token estimation ---

def estimate_tokens(messages: list[dict]) -> int:
    """Estimate token count using chars/4 heuristic."""
    total_chars = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    total_chars += len(json.dumps(block))
    return total_chars // 4


def compact_session(messages: list[dict]) -> list[dict]:
    """
    Compact a session by summarizing old messages and keeping recent ones.

    Strategy: Split into old (to summarize) and recent (to keep verbatim).
    Use Claude to summarize the old part into a single assistant message.
    """
    if len(messages) <= RECENT_KEEP:
        return messages

    old_messages = messages[:-RECENT_KEEP]
    recent_messages = messages[-RECENT_KEEP:]

    # Build a text representation of old messages for summarization
    old_text_parts = []
    for msg in old_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, str):
            old_text_parts.append(f"{role}: {content[:500]}")
        elif isinstance(content, list):
            # Summarize tool calls briefly
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        old_text_parts.append(f"{role}: {block.get('text', '')[:500]}")
                    elif block.get("type") == "tool_use":
                        old_text_parts.append(f"{role}: [called {block.get('name', 'tool')}]")
                    elif block.get("type") == "tool_result":
                        old_text_parts.append(f"tool_result: {str(block.get('content', ''))[:200]}")

    old_text = "\n".join(old_text_parts)

    # Ask Claude to summarize
    summary_response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"Summarize this conversation history concisely, preserving key facts, decisions, and context:\n\n{old_text}",
        }],
    )

    summary = summary_response.content[0].text
    print(f"  [compaction] Summarized {len(old_messages)} messages into summary ({len(summary)} chars)")

    # Return: summary as first assistant message + recent messages
    compacted = [
        {"role": "user", "content": "[Previous conversation summary follows]"},
        {"role": "assistant", "content": f"[Summary of earlier conversation]\n{summary}"},
    ] + recent_messages

    return compacted


# --- Permission system ---

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


# --- Agent loop with compaction ---

def run_agent_turn(user_id: str, user_text: str) -> str:
    messages = load_session(user_id)
    messages.append({"role": "user", "content": user_text})

    # Check if compaction is needed
    tokens = estimate_tokens(messages)
    if tokens > TOKEN_THRESHOLD:
        print(f"  [compaction] Session has ~{tokens} tokens, compacting...")
        messages = compact_session(messages)
        save_session(user_id, messages)

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


# --- Channel: Telegram ---

async def handle_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_text = update.message.text
    await update.message.reply_text("Working on it...")
    reply = run_agent_turn(user_id, user_text)
    await update.message.reply_text(reply[:4096])


def start_telegram():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram))
    print("[telegram] Bot is running!")
    app.run_polling()


# --- Channel: HTTP ---

flask_app = Flask(__name__)


@flask_app.route("/chat", methods=["POST"])
def http_chat():
    data = request.get_json()
    user_id = data.get("user_id", "http-user")
    message = data.get("message", "")
    reply = run_agent_turn(user_id, message)
    return jsonify({"reply": reply})


@flask_app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


def start_http():
    flask_app.run(host="0.0.0.0", port=5000, debug=False)


# --- Main ---

def main():
    print("Starting gateway with context compaction...")
    print(f"  Token threshold: {TOKEN_THRESHOLD}")
    print(f"  Recent messages kept: {RECENT_KEEP}")

    http_thread = threading.Thread(target=start_http, daemon=True)
    http_thread.start()

    start_telegram()


if __name__ == "__main__":
    main()
