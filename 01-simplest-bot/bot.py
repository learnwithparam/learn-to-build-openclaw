#!/usr/bin/env python3
"""
01: The Simplest Bot — A 20-line bot powered by OpenRouter + qwen3-coder.

This is the "Hello World" of AI assistants. It proves that a working
AI bot needs nothing more than:
  1. A message handler (Telegram or CLI)
  2. An OpenRouter API call
  3. Send the response back

Stateless — no memory between messages. Each message is independent.

Usage:
    uv run python 01-simplest-bot/bot.py            # CLI mode (no Telegram needed)
    uv run python 01-simplest-bot/bot.py --telegram # Telegram bot mode
"""
import os
import sys

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


def ask(user_text: str) -> str:
    """One stateless call to the LLM."""
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": user_text}],
    )
    return response.choices[0].message.content or ""


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Telegram handler — just forwards the message to ask()."""
    reply = ask(update.message.text)
    await update.message.reply_text(reply)


def run_telegram():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print(f"Telegram bot running with model: {MODEL}")
    app.run_polling()


def run_cli():
    print(f"OpenClaw CLI — model: {MODEL}. Type 'exit' to quit.\n")
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
        print(f"bot> {ask(user_text)}\n")


def main():
    if "--telegram" in sys.argv:
        run_telegram()
    else:
        run_cli()


if __name__ == "__main__":
    main()
