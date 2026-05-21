# 04 Guide: Tools & Agent Loop

## The Biggest Jump

Module 03 was a chatbot — it could only respond with text. Module 04 is an agent — it can take actions in the real world. The difference is tools and the agent loop.

## Tool Schema Design

Each tool follows the OpenAI function-calling schema (which OpenRouter supports for every model that does tool use):

```python
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
}
```

The model reads these definitions and decides when/how to use each tool. Good descriptions are critical — they're how the model understands what each tool does.

## The Agent Loop

This is the core pattern behind every AI agent:

```python
while True:
    messages = [{"role": "system", "content": SOUL}] + history
    response = client.chat.completions.create(
        model=MODEL,
        tools=TOOLS,
        messages=messages,
    )

    msg = response.choices[0].message
    # Append assistant message (with tool_calls if any) to history
    history.append({"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls or None})

    # If the model didn't call any tools, we're done
    if not msg.tool_calls:
        return msg.content or "Done."

    # Execute tools, append results as 'tool' messages
    for tc in msg.tool_calls:
        args = json.loads(tc.function.arguments)
        result = execute_tool(tc.function.name, args)
        history.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    # Loop continues — model sees tool results and decides next action
```

The key insight: **the model decides when to stop**. It keeps calling tools until it has enough information to answer, then it responds with text and `msg.tool_calls` is empty.

## Tool Calls Shape

In OpenAI/OpenRouter responses, an assistant message can have both text content AND a list of tool calls:

```python
msg = response.choices[0].message
msg.content      # "Let me check that file."  (may be None when only calling tools)
msg.tool_calls   # [ToolCall(id="call_abc", function=Function(name="read_file", arguments='{"path": "bot.py"}'))]
```

Note that `arguments` is a **JSON string**, not a dict — you call `json.loads()` to decode it. A single response can contain both text and tool calls, so we always handle both when building the message history.

## The execute_tool Dispatch Pattern

```python
def execute_tool(name, input):
    if name == "run_command":
        return subprocess.run(input["command"], ...)
    elif name == "read_file":
        return Path(input["path"]).read_text()
    ...
```

Simple if/elif dispatch. Each tool handler:
1. Extracts its parameters from `input`
2. Performs the action
3. Returns a string result

The result goes back into the conversation as a `tool_result` message, and the model sees it on the next loop iteration.

## Tool Results in Message History

A tool result lives in its own message with `role: "tool"` and the matching `tool_call_id`:

```python
history.append({
    "role": "tool",
    "tool_call_id": tc.id,       # Must match the assistant's tool_call id
    "content": result_string,
})
```

This is how the model knows which result corresponds to which tool call. If the assistant requested two tools in parallel, you append two `role: "tool"` messages — one per call.

## Session Storage Changes

In module 02, we stored plain user/assistant messages. Now an assistant message can also carry a `tool_calls` list:

```json
{"role": "user",      "content": "What files are here?"}
{"role": "assistant", "content": "", "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "run_command", "arguments": "{\"command\": \"ls\"}"}}]}
{"role": "tool",      "tool_call_id": "call_1", "content": "bot.py\nREADME.md"}
{"role": "assistant", "content": "There are two files: bot.py and README.md."}
```

This is why we switch from `append_message` to `save_session` — the full session gets rewritten after each agent turn so the tool-call / tool-result IDs stay paired correctly.

---

**The loop is the agent. Tools are just functions. The model decides everything.**

[<- README](./README.md) | [Next: Permission Controls ->](../05-permission-controls/GUIDE.md)
