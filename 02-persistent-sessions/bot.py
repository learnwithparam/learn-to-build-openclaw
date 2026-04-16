#!/usr/bin/env python3
"""
02: Persistent Sessions — JSONL per-user session storage.

Builds on 01 by adding:
  - Per-user session files (JSONL format)
  - Multi-turn conversation memory
  - Crash-safe append-only persistence

Each user gets their own session file in ./sessions/{user_id}.jsonl.

Usage:
    uv run python 02-persistent-sessions/bot.py
"""
import json
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

load_dotenv(override=True)

MODEL = "claude-sonnet-4-20250514"
client = Anthropic()

SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)


# --- Session persistence (JSONL) ---

def load_session(user_id: str) -> list[dict]:
    """Load conversation history from a JSONL file."""
    path = SESSIONS_DIR / f"{user_id}.jsonl"
    if not path.exists():
        return []
    messages = []
    for line in path.read_text().splitlines():
        if line.strip():
            messages.append(json.loads(line))
    return messages


def append_message(user_id: str, message: dict):
    """Append a single message to the user's JSONL session file."""
    path = SESSIONS_DIR / f"{user_id}.jsonl"
    with open(path, "a") as f:
        f.write(json.dumps(message) + "\n")


# --- Bot handler ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle a message with full conversation history."""
    user_id = str(update.effective_user.id)
    user_text = update.message.text

    # Load existing conversation
    messages = load_session(user_id)

    # Add the new user message
    user_msg = {"role": "user", "content": user_text}
    messages.append(user_msg)
    append_message(user_id, user_msg)

    # Call Claude with full history
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=messages,
    )

    reply = response.content[0].text

    # Save assistant response
    assistant_msg = {"role": "assistant", "content": reply}
    append_message(user_id, assistant_msg)

    await update.message.reply_text(reply)


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print(f"Bot is running! Sessions stored in {SESSIONS_DIR}")
    app.run_polling()


if __name__ == "__main__":
    main()
