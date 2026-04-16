# 01 Guide: The Simplest Bot

## Why Start Here

Every AI assistant — OpenClaw, ChatGPT, Claude — started as something like this: take user input, send it to an LLM, return the response. Before adding persistence, tools, or personality, you need to understand the minimal viable bot.

## Telegram Bot Architecture

Telegram bots work through a simple polling model:

```
Telegram Server
    |
    | (HTTP long-poll)
    v
python-telegram-bot library
    |
    | (dispatches to handlers)
    v
handle_message(update, context)
    |
    | (Anthropic API call)
    v
response.content[0].text -> reply_text()
```

The `python-telegram-bot` library handles all the HTTP communication with Telegram's servers. You just write handler functions.

## The API Call Anatomy

```python
response = client.messages.create(
    model=MODEL,
    max_tokens=1024,
    messages=[{"role": "user", "content": user_text}],
)
```

This single call is doing a lot:
- `model` — Which Claude model to use
- `max_tokens` — Maximum response length
- `messages` — The conversation history (just one message here)

The response contains `content`, which is a list of content blocks. For text responses, `response.content[0].text` gives you the reply.

## What Makes This Stateless

Notice the `messages` array: it only contains the current user message. There's no history. Each API call is completely independent.

This means:
- The bot can't have multi-turn conversations
- It can't remember anything you told it
- Every message starts from scratch

This is the problem we solve in module 02.

## Why Telegram

Telegram is an ideal platform for building AI bots:
- Free bot API with no approval process
- Real-time message delivery
- Rich message formatting (markdown, buttons, etc.)
- Easy to test on your phone

But the assistant logic we build is not tied to Telegram — by module 06, we'll have it working over HTTP too.

## What's Missing (and Why)

| Feature | Status | Added In |
|---------|--------|----------|
| Conversation history | Missing | [02: Persistent Sessions](../02-persistent-sessions/) |
| Personality | Missing | [03: Personality & Soul](../03-personality-soul/) |
| Tool use | Missing | [04: Tools & Agent Loop](../04-tools-agent-loop/) |
| Safety controls | Missing | [05: Permission Controls](../05-permission-controls/) |

That's the point — you don't need any of it for a working bot.

---

**A message handler and an API call. That's all a bot is.**

[<- README](./README.md) | [Next: Persistent Sessions ->](../02-persistent-sessions/GUIDE.md)
