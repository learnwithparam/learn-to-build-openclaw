#!/usr/bin/env python3
"""
08: Long-Term Memory — Persistent knowledge that outlives sessions.

Builds on 07 by adding:
  - save_memory tool — writes facts to ./memory/ as markdown files
  - memory_search tool — keyword-based search across memory files
  - Updated SOUL with memory instructions
  - Cross-session recall of saved knowledge

Usage:
    uv run python 08-long-term-memory/bot.py
"""
import json
import os
import re
import subprocess
import threading
from datetime import datetime
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
MEMORY_DIR = BOT_DIR / "memory"
MEMORY_DIR.mkdir(exist_ok=True)

# Enhanced SOUL with memory instructions
SOUL = """# OpenClaw

You are OpenClaw, a personal AI assistant running on Telegram.

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
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    total_chars += len(json.dumps(block))
    return total_chars // 4


def compact_session(messages: list[dict]) -> list[dict]:
    if len(messages) <= RECENT_KEEP:
        return messages

    old_messages = messages[:-RECENT_KEEP]
    recent_messages = messages[-RECENT_KEEP:]

    old_text_parts = []
    for msg in old_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, str):
            old_text_parts.append(f"{role}: {content[:500]}")
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        old_text_parts.append(f"{role}: {block.get('text', '')[:500]}")
                    elif block.get("type") == "tool_use":
                        old_text_parts.append(f"{role}: [called {block.get('name', 'tool')}]")

    old_text = "\n".join(old_text_parts)
    summary_response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"Summarize this conversation concisely, preserving key facts:\n\n{old_text}",
        }],
    )
    summary = summary_response.content[0].text
    print(f"  [compaction] Summarized {len(old_messages)} messages")

    return [
        {"role": "user", "content": "[Previous conversation summary follows]"},
        {"role": "assistant", "content": f"[Summary of earlier conversation]\n{summary}"},
    ] + recent_messages


# --- Memory system ---

def save_memory(topic: str, content: str) -> str:
    """Save a memory to a markdown file."""
    # Sanitize topic for filename
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
        # Simple keyword matching
        matches = sum(1 for word in query_words if word in text.lower())
        if matches > 0:
            results.append((matches, filepath.stem, text[:500]))

    if not results:
        return "No memories found matching that query."

    results.sort(reverse=True)  # Most matches first
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


# --- Tool definitions (now with memory tools) ---

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
    {
        "name": "save_memory",
        "description": "Save an important fact or piece of knowledge to long-term memory. Use for user preferences, facts, and important context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic/category for the memory (e.g., 'user-preferences', 'project-details')"},
                "content": {"type": "string", "description": "The information to remember"},
            },
            "required": ["topic", "content"],
        },
    },
    {
        "name": "memory_search",
        "description": "Search long-term memory for previously saved knowledge. Use before answering questions about the user or recalling past context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords"}
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
            return "Error: Command timed out."
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
    elif name == "save_memory":
        return save_memory(input["topic"], input["content"])
    elif name == "memory_search":
        return memory_search(input["query"])
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
    messages = load_session(user_id)
    messages.append({"role": "user", "content": user_text})

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
    print("Starting bot with long-term memory...")
    print(f"  Memory directory: {MEMORY_DIR}")

    http_thread = threading.Thread(target=start_http, daemon=True)
    http_thread.start()

    start_telegram()


if __name__ == "__main__":
    main()
