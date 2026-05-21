#!/usr/bin/env python3
"""
08: Long-Term Memory — Persistent knowledge that outlives sessions.

Builds on 07 by adding:
  - save_memory tool — writes facts to ./memory/ as markdown files
  - memory_search tool — keyword-based search across memory files
  - Updated SOUL with memory instructions
  - Cross-session recall of saved knowledge

Usage:
    uv run python 08-long-term-memory/bot.py            # CLI
    uv run python 08-long-term-memory/bot.py --http     # CLI + HTTP
    uv run python 08-long-term-memory/bot.py --telegram # Telegram + HTTP
"""
import json
import os
import re
import subprocess
import sys
import threading
from datetime import datetime
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
MEMORY_DIR = BOT_DIR / "memory"
MEMORY_DIR.mkdir(exist_ok=True)

# Enhanced SOUL with memory instructions
SOUL = """# OpenClaw

You are OpenClaw, a personal AI assistant.

## Personality
- Helpful, concise, and technically competent
- You explain things clearly but don't over-explain
- Friendly but professional tone

## Boundaries
- Don't pretend to browse the internet
- Don't make up information

## Memory Strategy
- When the user shares important facts (preferences, name, work, projects), proactively use save_memory to store them
- Before answering questions about the user, check memory_search first
- Reference remembered facts naturally in conversation
- Save memories with descriptive topics for easy retrieval later
"""

# Compaction settings
TOKEN_THRESHOLD = 50000
RECENT_KEEP = 10


# --- Token estimation & compaction ---

def estimate_tokens(messages: list[dict]) -> int:
    total_chars = 0
    for msg in messages:
        content = msg.get("content") or ""
        total_chars += len(content)
        for tc in msg.get("tool_calls", []) or []:
            total_chars += len(json.dumps(tc))
    return total_chars // 4


def compact_session(messages: list[dict]) -> list[dict]:
    if len(messages) <= RECENT_KEEP:
        return messages

    old_messages = messages[:-RECENT_KEEP]
    recent_messages = messages[-RECENT_KEEP:]

    old_text_parts = []
    for msg in old_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content") or ""
        if content:
            old_text_parts.append(f"{role}: {content[:500]}")
        for tc in msg.get("tool_calls", []) or []:
            name = tc.get("function", {}).get("name", "tool")
            old_text_parts.append(f"{role}: [called {name}]")

    old_text = "\n".join(old_text_parts)
    summary_response = client.chat.completions.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"Summarize this conversation concisely, preserving key facts:\n\n{old_text}",
        }],
    )
    summary = summary_response.choices[0].message.content or ""
    print(f"  [compaction] Summarized {len(old_messages)} messages")

    return [
        {"role": "user", "content": "[Previous conversation summary follows]"},
        {"role": "assistant", "content": f"[Summary of earlier conversation]\n{summary}"},
    ] + recent_messages


# --- Memory system ---

def save_memory(topic: str, content: str) -> str:
    """Save a memory to a markdown file."""
    filename = re.sub(r'[^\w\s-]', '', topic).strip().replace(' ', '-').lower()
    if not filename:
        filename = "misc"
    filepath = MEMORY_DIR / f"{filename}.md"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## {topic} ({timestamp})\n{content}\n"

    with open(filepath, "a") as f:
        f.write(entry)

    return f"Saved memory about '{topic}' to {filepath.name}"


def memory_search(query: str) -> str:
    """Search memory files for keywords."""
    query_words = query.lower().split()
    results = []

    for filepath in MEMORY_DIR.glob("*.md"):
        text = filepath.read_text()
        matches = sum(1 for word in query_words if word in text.lower())
        if matches > 0:
            results.append((matches, filepath.stem, text[:500]))

    if not results:
        return "No memories found matching that query."

    results.sort(reverse=True)
    output_parts = []
    for score, name, text in results[:5]:
        output_parts.append(f"--- {name} (relevance: {score}) ---\n{text}")

    return "\n\n".join(output_parts)


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


# --- Tool definitions (with memory tools) ---

TOOLS = [
    {"type": "function", "function": {"name": "run_command", "description": "Run a shell command. Subject to safety checks.",
        "parameters": {"type": "object", "properties": {"command": {"type": "string", "description": "The shell command to execute"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read the contents of a file.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Path to the file to read"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write content to a file, creating directories as needed.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Path to write to"}, "content": {"type": "string", "description": "Content to write"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "web_search", "description": "Search the web (placeholder).",
        "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "save_memory",
        "description": "Save an important fact or piece of knowledge to long-term memory. Use for user preferences, facts, and important context.",
        "parameters": {"type": "object", "properties": {
            "topic": {"type": "string", "description": "Topic/category for the memory (e.g., 'user-preferences', 'project-details')"},
            "content": {"type": "string", "description": "The information to remember"},
        }, "required": ["topic", "content"]}}},
    {"type": "function", "function": {"name": "memory_search",
        "description": "Search long-term memory for previously saved knowledge. Use before answering questions about the user or recalling past context.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Search keywords"}}, "required": ["query"]}}},
]


def execute_tool(name: str, args: dict) -> str:
    if name == "run_command":
        command = args["command"]
        safety = check_command_safety(command)
        if safety == "blocked":
            return f"BLOCKED: Command '{command}' matches a dangerous pattern."
        if safety == "needs_approval":
            save_approval(command)
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            return (result.stdout + result.stderr)[:10000] or "Command completed with no output."
        except subprocess.TimeoutExpired:
            return "Error: Command timed out."
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
    elif name == "save_memory":
        return save_memory(args["topic"], args["content"])
    elif name == "memory_search":
        return memory_search(args["query"])
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
    history = load_session(user_id)
    history.append({"role": "user", "content": user_text})

    tokens = estimate_tokens(history)
    if tokens > TOKEN_THRESHOLD:
        print(f"  [compaction] Session has ~{tokens} tokens, compacting...")
        history = compact_session(history)
        save_session(user_id, history)

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


# --- Channels ---

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
    return jsonify({"status": "ok", "model": MODEL})


def start_http():
    print("[http] Server running on http://localhost:5000")
    flask_app.run(host="0.0.0.0", port=5000, debug=False)


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


def main():
    print(f"OpenClaw 08 — memory at {MEMORY_DIR}")

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
