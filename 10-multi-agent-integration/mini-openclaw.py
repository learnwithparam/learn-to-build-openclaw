#!/usr/bin/env python3
"""
10: Multi-Agent Integration — The full mini-OpenClaw system.

The final module brings everything together:
  - Multiple specialized agents (general + research)
  - Prefix-based routing (/research triggers the research agent)
  - Separate sessions per agent, shared memory
  - REPL interface for local testing
  - All previous features: sessions, SOUL, tools, permissions,
    compaction, memory, locking, scheduling

Workspace: ~/.mini-openclaw/

Usage:
    uv run python 10-multi-agent-integration/mini-openclaw.py
"""
import json
import re
import subprocess
import threading
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import schedule
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

MODEL = "claude-sonnet-4-20250514"
client = Anthropic()

# Use a home-directory workspace like the real OpenClaw
WORKSPACE = Path.home() / ".mini-openclaw"
SESSIONS_DIR = WORKSPACE / "sessions"
MEMORY_DIR = WORKSPACE / "memory"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# --- Agent configurations ---

AGENTS = {
    "general": {
        "name": "OpenClaw",
        "soul": """# OpenClaw (General Agent)

You are OpenClaw, a personal AI assistant.

## Personality
- Helpful, concise, and technically competent
- Friendly but professional tone

## Capabilities
- Run commands, read/write files
- Save and search long-term memory
- Answer questions, help with tasks

## Memory Strategy
- Proactively save important user facts
- Search memory before answering personal questions
""",
        "tools": ["run_command", "read_file", "write_file", "web_search", "save_memory", "memory_search"],
    },
    "research": {
        "name": "OpenClaw Research",
        "soul": """# OpenClaw (Research Agent)

You are OpenClaw's research specialist. You focus on in-depth analysis and investigation.

## Personality
- Thorough and analytical
- Provides structured, well-organized findings
- Cites sources and explains reasoning

## Capabilities
- Deep file analysis and code review
- Research synthesis and comparison
- Save findings to shared memory for other agents

## Memory Strategy
- Save research findings with detailed topics
- Search existing memory to avoid duplicate research
""",
        "tools": ["run_command", "read_file", "web_search", "save_memory", "memory_search"],
    },
}

# Route prefix -> agent name
ROUTE_PREFIXES = {
    "/research": "research",
}

DEFAULT_AGENT = "general"

# Compaction settings
TOKEN_THRESHOLD = 50000
RECENT_KEEP = 10

# Per-session locking
session_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)


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
    return [
        {"role": "user", "content": "[Previous conversation summary follows]"},
        {"role": "assistant", "content": f"[Summary]\n{summary}"},
    ] + recent_messages


# --- Memory system (shared across agents) ---

def save_memory_fn(topic: str, content: str) -> str:
    filename = re.sub(r'[^\w\s-]', '', topic).strip().replace(' ', '-').lower()
    if not filename:
        filename = "misc"
    filepath = MEMORY_DIR / f"{filename}.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## {topic} ({timestamp})\n{content}\n"
    with open(filepath, "a") as f:
        f.write(entry)
    return f"Saved memory about '{topic}' to {filepath.name}"


def memory_search_fn(query: str) -> str:
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

APPROVALS_FILE = WORKSPACE / "exec-approvals.json"


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


# --- All tool definitions ---

ALL_TOOLS = {
    "run_command": {
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
    "read_file": {
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
    "write_file": {
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
    "web_search": {
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
    "save_memory": {
        "name": "save_memory",
        "description": "Save an important fact to shared long-term memory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic/category for the memory"},
                "content": {"type": "string", "description": "The information to remember"},
            },
            "required": ["topic", "content"],
        },
    },
    "memory_search": {
        "name": "memory_search",
        "description": "Search shared long-term memory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords"}
            },
            "required": ["query"],
        },
    },
}


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
        return save_memory_fn(input["topic"], input["content"])
    elif name == "memory_search":
        return memory_search_fn(input["query"])
    return f"Unknown tool: {name}"


# --- Session persistence ---

def load_session(session_id: str) -> list[dict]:
    path = SESSIONS_DIR / f"{session_id}.jsonl"
    if not path.exists():
        return []
    messages = []
    for line in path.read_text().splitlines():
        if line.strip():
            messages.append(json.loads(line))
    return messages


def save_session(session_id: str, messages: list[dict]):
    path = SESSIONS_DIR / f"{session_id}.jsonl"
    with open(path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")


# --- Agent routing ---

def resolve_agent(user_text: str) -> tuple[str, str]:
    """
    Route a message to the appropriate agent based on prefix.
    Returns (agent_name, cleaned_text).
    """
    for prefix, agent_name in ROUTE_PREFIXES.items():
        if user_text.lower().startswith(prefix):
            cleaned = user_text[len(prefix):].strip()
            return agent_name, cleaned or user_text
    return DEFAULT_AGENT, user_text


# --- Agent loop ---

def run_agent_turn(session_id: str, user_text: str, agent_name: str | None = None) -> str:
    """Run an agent turn with routing, locking, compaction, and tools."""
    # Route to agent if not specified
    if agent_name is None:
        agent_name, user_text = resolve_agent(user_text)

    agent_config = AGENTS[agent_name]
    agent_tools = [ALL_TOOLS[t] for t in agent_config["tools"]]

    # Use agent-specific session: {session_id}:{agent_name}
    full_session_id = f"{session_id}:{agent_name}"

    with session_locks[full_session_id]:
        messages = load_session(full_session_id)
        messages.append({"role": "user", "content": user_text})

        tokens = estimate_tokens(messages)
        if tokens > TOKEN_THRESHOLD:
            messages = compact_session(messages)
            save_session(full_session_id, messages)

        while True:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=agent_config["soul"],
                tools=agent_tools,
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
                save_session(full_session_id, messages)
                text_parts = [b.text for b in response.content if hasattr(b, "text")]
                return "\n".join(text_parts) or "Done."

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [{agent_name}] {block.name}({json.dumps(block.input)[:100]})")
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})


# --- Scheduled tasks ---

def heartbeat_task():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"  [cron] Running heartbeat at {timestamp}")
    try:
        run_agent_turn(
            "cron:heartbeat",
            f"It is {timestamp}. Check memory for any interesting patterns or reminders.",
            agent_name="general",
        )
    except Exception as e:
        print(f"  [cron] Error: {e}")


def setup_heartbeats():
    schedule.every(24).hours.do(heartbeat_task)


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)


# --- REPL interface ---

def repl():
    """Interactive REPL for local testing."""
    user_id = "repl-user"
    print(f"\nMini-OpenClaw REPL")
    print(f"Workspace: {WORKSPACE}")
    print(f"Agents: {', '.join(AGENTS.keys())}")
    print(f"Prefix /research to use the research agent")
    print(f"Type 'q' to quit.\n")

    while True:
        try:
            user_input = input("\033[36m>> \033[0m")
            if user_input.lower() in ("q", "quit", "exit"):
                break
            if not user_input.strip():
                continue

            reply = run_agent_turn(user_id, user_input)
            print(f"\n{reply}\n")
        except (EOFError, KeyboardInterrupt):
            break

    print("\nGoodbye!")


# --- Main ---

def main():
    print("=" * 60)
    print("  Mini-OpenClaw — Multi-Agent AI Assistant")
    print("=" * 60)
    print(f"\nWorkspace: {WORKSPACE}")
    print(f"Sessions:  {SESSIONS_DIR}")
    print(f"Memory:    {MEMORY_DIR}")
    print(f"Agents:    {', '.join(AGENTS.keys())}")

    # Start scheduler
    setup_heartbeats()
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    # Start REPL
    repl()


if __name__ == "__main__":
    main()
