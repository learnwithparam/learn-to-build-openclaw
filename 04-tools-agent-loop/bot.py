#!/usr/bin/env python3
"""
04: Tools & Agent Loop — From chatbot to agent.

Builds on 03 by adding:
  - 4 tools: run_command, read_file, write_file, web_search
  - The agent loop (call tools until done)
  - OpenAI tool-call format for OpenRouter compatibility
  - Tool dispatch pattern

Usage:
    uv run python 04-tools-agent-loop/bot.py            # CLI mode
    uv run python 04-tools-agent-loop/bot.py --telegram # Telegram mode
"""
import json
import os
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

# --- Tool definitions (OpenAI format) ---

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command and return stdout + stderr.",
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
                    "path": {"type": "string", "description": "Path to the file to write"},
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
            "description": "Search the web for information. Returns a simulated result (placeholder).",
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
    """Dispatch a tool call to the appropriate handler."""
    if name == "run_command":
        try:
            result = subprocess.run(
                args["command"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
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
        return f"[Web search placeholder] Query: {args['query']}. In a production system, this would call a search API."

    return f"Unknown tool: {name}"


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


def save_session(user_id: str, messages: list[dict]):
    """Overwrite the session file with all messages."""
    path = SESSIONS_DIR / f"{user_id}.jsonl"
    with open(path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")


# --- Agent loop ---

def run_agent_turn(user_id: str, user_text: str) -> str:
    """Run the agent loop: call the LLM with tools until it stops calling them."""
    history = load_session(user_id)
    history.append({"role": "user", "content": user_text})

    while True:
        # Prepend system prompt for the call (not saved to history)
        messages = [{"role": "system", "content": SOUL}] + history

        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=4096,
            tools=TOOLS,
            messages=messages,
        )

        msg = response.choices[0].message

        # Build the assistant message for history.
        # OpenAI shape: {"role": "assistant", "content": str|None, "tool_calls": [...]}
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

        # If the model didn't call any tools, we're done
        if not msg.tool_calls:
            save_session(user_id, history)
            return msg.content or "Done."

        # Execute each tool call and add results
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
        # Loop continues — feed tool results back to the model


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
    print(f"Agent bot running with tools — model: {MODEL}")
    app.run_polling()


# --- CLI channel ---

def run_cli():
    user_id = "cli-user"
    print(f"OpenClaw CLI (agent + tools) — model: {MODEL}. Type 'exit' to quit.\n")
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
