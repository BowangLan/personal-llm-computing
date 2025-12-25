import asyncio
import json
import logging
import time
from typing import List

from claude_agent_sdk import query, ClaudeAgentOptions
from observability import log_event

_logger = logging.getLogger("bot.claude_code_test")


async def llm_reply(user_input: str) -> str:
    """General chat response for normal text messages."""
    t0 = time.perf_counter()

    prompt = f"""You are a helpful assistant in a Telegram chat.
Answer clearly and concisely.
If the user asks you to run shell commands, tell them to prefix with 'run:' and describe what will happen.

User message: {user_input}"""

    reply = ""
    print("Querying...")
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Bash", "Glob", "WebSearch", "WebFetch"]
        ),
    ):
        if hasattr(message, "result"):
            reply += message.text

    reply = reply.strip() or "(empty response)"
    print("Reply:", reply)
    return reply


async def main():
    async for message in query(
        prompt="What is the weather in Tokyo?",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Bash", "Glob", "WebSearch", "WebFetch"]
        ),
    ):
        # if hasattr(message, "result"):
            # print(message.result)
        print("\n--------------------------------")
        if hasattr(message, "tool_calls"):
            print("tool_calls")
            print(message.tool_calls)
        
        if hasattr(message, "content"):
            print("content")
            print(message.content)

        if hasattr(message, "result"):
            print("result")
            print(message.result)



if __name__ == "__main__":
    # asyncio.run(llm_reply("What is the weather in Tokyo?"))
    asyncio.run(main())
