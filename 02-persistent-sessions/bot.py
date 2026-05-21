#!/usr/bin/env python3
"""
02: Persistent Sessions — JSONL per-user session storage.

Builds on 01 by adding:
  - Per-user session files (JSONL format)
  - Multi-turn conversation memory
  - Crash-safe append-only persistence

Each user gets their own session file in ./sessions/{user_id}.jsonl.

Usage:
    uv run python 02-persistent-sessions/bot.py            # CLI mode
    uv run python 02-persistent-sessions/bot.py --telegram # Telegram mode
"""
import json
import os
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


# --- Core: stateful one-shot ---

def reply_with_history(user_id: str, user_text: str) -> str:
    """Load history, append user msg, call LLM, save reply, return reply."""
    messages = load_session(user_id)

    user_msg = {"role": "user", "content": user_text}
    messages.append(user_msg)
    append_message(user_id, user_msg)

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=1024,
        messages=messages,
    )
    reply = response.choices[0].message.content or ""

    assistant_msg = {"role": "assistant", "content": reply}
    append_message(user_id, assistant_msg)

    return reply


# --- Telegram channel ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    reply = reply_with_history(user_id, update.message.text)
    await update.message.reply_text(reply)


def run_telegram():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print(f"Telegram bot running — sessions stored in {SESSIONS_DIR}")
    app.run_polling()


# --- CLI channel ---

def run_cli():
    user_id = "cli-user"
    print(f"OpenClaw CLI — model: {MODEL}, session: {user_id}. Type 'exit' to quit.\n")
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
        print(f"bot> {reply_with_history(user_id, user_text)}\n")


def main():
    if "--telegram" in sys.argv:
        run_telegram()
    else:
        run_cli()


if __name__ == "__main__":
    main()
