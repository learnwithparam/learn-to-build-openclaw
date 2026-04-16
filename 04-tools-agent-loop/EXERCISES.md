# 04 Exercises — Tools & Agent Loop

## Exercise 1: Watch the Agent Loop

**Goal**: See the agent loop in action.

1. Run the bot: `make 04-tools-agent-loop`
2. Send: "Create a file called hello.py that prints 'Hello World', then run it."
3. Watch the terminal output — you should see multiple tool calls:
   - `write_file` to create the file
   - `run_command` to execute it
4. Count how many loop iterations the agent takes.

**Checkpoint**: The agent should create and run the file, making at least 2 tool calls.

---

## Exercise 2: Trace the Tool Calls

**Goal**: Understand the full request/response cycle.

1. Send: "What files are in the current directory?"
2. Look at the console output to see which tool was called and with what arguments
3. Now send: "Read the contents of bot.py and summarize it"
4. Trace the flow: tool call -> result -> model processes result -> final response

**Checkpoint**: You should see `run_command` or `read_file` calls and their results in the console.

---

## Exercise 3: Add a New Tool

**Goal**: Extend the agent with a custom tool.

1. Add a `list_directory` tool to the TOOLS array:
   ```python
   {
       "name": "list_directory",
       "description": "List files and directories at the given path.",
       "input_schema": {
           "type": "object",
           "properties": {
               "path": {"type": "string", "description": "Directory path to list"}
           },
           "required": ["path"],
       },
   }
   ```
2. Add the handler in `execute_tool`:
   ```python
   elif name == "list_directory":
       entries = os.listdir(input.get("path", "."))
       return "\n".join(entries)
   ```
3. Test it: "What's in the parent directory?"

**Checkpoint**: The agent should prefer `list_directory` over `run_command` for listing files.

---

## Exercise 4: Count Loop Iterations

**Goal**: Understand when the agent decides to stop.

1. Add a counter to the agent loop in `run_agent_turn`:
   ```python
   iterations = 0
   while True:
       iterations += 1
       print(f"  [loop iteration {iterations}]")
       ...
   ```
2. Try these prompts and record the iteration counts:
   - "What's 2 + 2?" (should be 1 — no tools needed)
   - "What files are here?" (should be 2 — one tool call + final response)
   - "Create a Python file, run it, then delete it" (should be 4+)

**Checkpoint**: Simple questions take 1 iteration. Complex tasks take many. The model decides.
