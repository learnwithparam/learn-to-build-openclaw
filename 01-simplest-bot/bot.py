#!/usr/bin/env python3
"""
01: The Simplest Bot — A 20-line Telegram + Claude bot.

This is the "Hello World" of AI assistants. It proves that a working
AI bot needs nothing more than:
  1. A Telegram bot handler
  2. An Anthropic API call
  3. Send the response back

Stateless — no memory between messages. Each message is independent.

Usage:
    uv run python 01-simplest-bot/bot.py
"""
import os

from anthropic import Anthropic
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

load_dotenv(override=True)

MODEL = "claude-sonnet-4-20250514"
client = Anthropic()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle every text message — call Claude, reply with the response."""
    user_text = update.message.text

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": user_text}],
    )

    reply = response.content[0].text
    await update.message.reply_text(reply)


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running! Send a message on Telegram.")
    app.run_polling()


if __name__ == "__main__":
    main()
