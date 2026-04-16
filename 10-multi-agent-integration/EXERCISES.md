# 10 Exercises — Multi-Agent Integration

## Exercise 1: Chat with Both Agents

**Goal**: Experience multi-agent routing.

1. Run mini-openclaw: `make 10-multi-agent-integration`
2. Chat normally (goes to general agent):
   ```
   >> What files are in the current directory?
   >> My name is Alice and I work on the Rocket project.
   ```
3. Use the research agent:
   ```
   >> /research Analyze the structure of this Python file and summarize the key patterns used.
   ```
4. Compare the response styles — research should be more thorough and structured

**Checkpoint**: Normal messages go to the general agent. `/research` messages go to the research agent. They have different personalities.

---

## Exercise 2: Test Cross-Agent Memory Sharing

**Goal**: Prove that agents share memory but not sessions.

1. Tell the general agent some facts:
   ```
   >> I prefer Python over JavaScript and I use VS Code.
   ```
2. Verify the general agent saved to memory (check `~/.mini-openclaw/memory/`)
3. Ask the research agent about the same topic:
   ```
   >> /research What do you know about my preferences?
   ```
4. The research agent should find the memory saved by the general agent

**Checkpoint**: Memory is shared. The research agent can access facts saved by the general agent.

---

## Exercise 3: Add a Third Agent

**Goal**: Extend the multi-agent system.

1. Add a "code-review" agent to the `AGENTS` dict:
   ```python
   "code-review": {
       "name": "OpenClaw Code Review",
       "soul": """You are a code review specialist. You focus on:
       - Code quality and best practices
       - Security vulnerabilities
       - Performance issues
       - Readability and maintainability
       Always provide specific, actionable feedback.""",
       "tools": ["read_file", "run_command", "save_memory", "memory_search"],
   }
   ```
2. Add the routing prefix: `"/review": "code-review"`
3. Test it:
   ```
   >> /review Read mini-openclaw.py and review the error handling.
   ```

**Checkpoint**: Your third agent should work with its own personality and session, while sharing memory with the other agents.

---

## Exercise 4: Design a Sub-Agent Spawning Pattern

**Goal**: Think about agent-initiated delegation.

1. Currently, users route to agents via prefixes. But what if the general agent could delegate to the research agent automatically?
2. Design a `delegate_to_agent` tool:
   - What parameters would it need? (agent_name, task_description)
   - How would you return the sub-agent's response?
   - Should the sub-agent have access to the parent's session?
3. Consider the risks:
   - Could agents get into infinite delegation loops?
   - How would you limit recursion depth?
   - How would you handle errors in sub-agent execution?

**Checkpoint**: You should understand that agent delegation is just another tool — `run_agent_turn()` called from within `execute_tool()`. Recursion limits and session isolation are the key safety mechanisms.
