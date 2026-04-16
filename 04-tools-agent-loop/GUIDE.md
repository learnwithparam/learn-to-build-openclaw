# 04 Guide: Tools & Agent Loop

## The Biggest Jump

Module 03 was a chatbot — it could only respond with text. Module 04 is an agent — it can take actions in the real world. The difference is tools and the agent loop.

## Tool Schema Design

Each tool is defined with a name, description, and input schema:

```python
{
    "name": "run_command",
    "description": "Run a shell command and return stdout + stderr.",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command to execute"}
        },
        "required": ["command"],
    },
}
```

The model reads these definitions and decides when/how to use each tool. Good descriptions are critical — they're how the model understands what each tool does.

## The Agent Loop

This is the core pattern behind every AI agent:

```python
while True:
    response = client.messages.create(
        model=MODEL,
        system=SOUL,
        tools=TOOLS,
        messages=messages,
    )

    # Append assistant message to history
    messages.append({"role": "assistant", "content": ...})

    # If no tool calls, we're done
    if response.stop_reason != "tool_use":
        return extract_text(response)

    # Execute tools, append results
    for block in response.content:
        if block.type == "tool_use":
            result = execute_tool(block.name, block.input)
            # Add tool result to messages

    # Loop continues — model sees tool results and decides next action
```

The key insight: **the model decides when to stop**. It keeps calling tools until it has enough information to answer, then it responds with text and `stop_reason` changes from `"tool_use"` to `"end_turn"`.

## Content Blocks

Anthropic's API returns content as a list of blocks, not a plain string:

```python
response.content = [
    TextBlock(type="text", text="Let me check that file."),
    ToolUseBlock(type="tool_use", id="toolu_123", name="read_file", input={"path": "bot.py"}),
]
```

A single response can contain both text and tool calls. You need to handle both when building the message history.

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

Tool results use a special format in the Anthropic API:

```python
messages.append({
    "role": "user",
    "content": [{
        "type": "tool_result",
        "tool_use_id": block.id,     # Must match the tool_use block's id
        "content": result_string,
    }]
})
```

Each `tool_result` must reference the `tool_use_id` from the assistant's request. This is how the model knows which result corresponds to which tool call.

## Session Storage Changes

In module 02, we stored simple text messages. Now we need to store structured content (text blocks + tool use blocks). The session format changes from:

```json
{"role": "assistant", "content": "Hello!"}
```

To:

```json
{"role": "assistant", "content": [{"type": "text", "text": "Let me check..."}, {"type": "tool_use", "id": "toolu_123", "name": "read_file", "input": {"path": "bot.py"}}]}
```

This is why we switch from `append_message` to `save_session` — the full session gets rewritten after each agent turn.

---

**The loop is the agent. Tools are just functions. The model decides everything.**

[<- README](./README.md) | [Next: Permission Controls ->](../05-permission-controls/GUIDE.md)
