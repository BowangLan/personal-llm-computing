import json
import logging
import time
from typing import List

from claude_agent_sdk import query, ClaudeAgentOptions
from observability import log_event

_logger = logging.getLogger("bot.ai")


async def parse_commands(user_input: str) -> List[str]:
    """Use LLM to extract multiple commands from natural language."""
    t0 = time.perf_counter()

    prompt = f"""Convert user request to bash commands.
Return one command per line, nothing else.
For multiple tasks, return multiple lines.
If unsafe or unclear, return: REFUSE

User request: {user_input}"""

    content = ""
    async for message in query(
        prompt=prompt, options=ClaudeAgentOptions(allowed_tools=[])
    ):
        if hasattr(message, "result"):
            content += message.result

    content = content.strip()
    if content == "REFUSE":
        log_event(
            _logger,
            "commands_refused",
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
        return []

    commands = [cmd.strip() for cmd in content.split("\n") if cmd.strip()]
    log_event(
        _logger,
        "commands_parsed",
        count=len(commands),
        duration_ms=int((time.perf_counter() - t0) * 1000),
    )
    return commands


async def llm_reply(user_input: str) -> str:
    """General chat response for normal text messages."""
    t0 = time.perf_counter()

    prompt = f"""You are a helpful assistant in a Telegram chat.
Answer clearly and concisely.
If the user asks you to run shell commands, tell them to prefix with 'run:' and describe what will happen.

User message: {user_input}"""

    reply = ""
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Bash", "Glob", "WebSearch", "WebFetch"]
        ),
    ):
        if hasattr(message, "result"):
            reply += message.result

    reply = reply.strip() or "(empty response)"
    log_event(
        _logger,
        "llm_reply_finished",
        input_len=len(user_input),
        output_len=len(reply),
        duration_ms=int((time.perf_counter() - t0) * 1000),
    )
    return reply
