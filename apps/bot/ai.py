import json
import logging
import time
from typing import List

from claude_agent_sdk import query, ClaudeAgentOptions
from observability import log_event
from persistence import Message

_logger = logging.getLogger("bot.ai")


async def parse_commands(user_input: str) -> List[str]:
    """Use LLM to extract multiple commands from natural language."""
    t0 = time.perf_counter()

    prompt = f"""Convert user request to bash commands.
If the request is safe and clear, provide commands.
If unsafe or unclear, set status to 'refused'.

User request: {user_input}"""

    schema = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["success", "refused"],
                "description": "Whether the request can be safely converted to commands"
            },
            "commands": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of bash commands to execute"
            }
        },
        "required": ["status", "commands"]
    }

    result = None
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=[],
            output_format={"type": "json_schema", "schema": schema}
        )
    ):
        if hasattr(message, "structured_output"):
            result = message.structured_output

    if not result or result.get("status") == "refused":
        log_event(
            _logger,
            "commands_refused",
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
        return []

    commands = [cmd.strip() for cmd in result.get("commands", []) if cmd.strip()]
    log_event(
        _logger,
        "commands_parsed",
        count=len(commands),
        duration_ms=int((time.perf_counter() - t0) * 1000),
    )
    return commands


async def generate_session_title(user_input: str) -> str:
    """
    Generate a concise title for a new session based on the first user message.
    Returns a short, descriptive title (max 50 chars).
    """
    t0 = time.perf_counter()

    prompt = f"""Generate a short, concise title (max 50 characters) for a conversation session based on this first user message.
The title should capture the main topic or intent.
Be specific and descriptive, but brief.

User message: {user_input}"""

    schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "A short, descriptive title for the session (max 50 chars)"
            }
        },
        "required": ["title"]
    }

    result = None
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=[],
            output_format={"type": "json_schema", "schema": schema}
        )
    ):
        if hasattr(message, "structured_output"):
            result = message.structured_output

    title = result.get("title", "New Session") if result else "New Session"
    # Ensure title is not too long
    if len(title) > 50:
        title = title[:47] + "..."

    log_event(
        _logger,
        "session_title_generated",
        title=title,
        duration_ms=int((time.perf_counter() - t0) * 1000),
    )
    return title


async def llm_reply(user_input: str, claude_session_id: str = None, working_dir: str = None) -> tuple[str, str]:
    """
    General chat response for normal text messages.
    Uses Claude's built-in session management for conversation continuity.
    If working_dir is provided, it will be set as the cwd for tool execution.
    Returns (response, claude_session_id) tuple.
    """
    t0 = time.perf_counter()

    # Build ClaudeAgentOptions
    options_kwargs = {
        "allowed_tools": ["Read", "Edit", "Bash", "Glob", "WebSearch", "WebFetch"],
        "permission_mode": "bypassPermissions"
    }

    if working_dir:
        options_kwargs["cwd"] = working_dir

    # If we have a Claude session ID, resume the session
    if claude_session_id:
        options_kwargs["resume"] = claude_session_id

    # For first message, provide a simple system context
    prompt = user_input
    if not claude_session_id:
        prompt = f"""You are a helpful assistant in a Telegram chat.
Answer clearly and concisely.
If the user asks you to run shell commands, tell them to prefix with 'run:' and describe what will happen.

User message: {user_input}"""

    reply = ""
    captured_session_id = claude_session_id

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(**options_kwargs),
    ):
        # Capture the session ID from the init message
        if hasattr(message, 'subtype') and message.subtype == 'init':
            captured_session_id = message.data.get('session_id')
            log_event(_logger, "claude_session_captured", session_id=captured_session_id)

        # Collect the text response
        if hasattr(message, "result") and message.result:
            reply += message.result

    reply = reply.strip() or "(empty response)"

    log_event(
        _logger,
        "llm_reply_finished",
        input_len=len(user_input),
        output_len=len(reply),
        has_working_dir=working_dir is not None,
        is_new_session=claude_session_id is None,
        duration_ms=int((time.perf_counter() - t0) * 1000),
    )

    return reply, captured_session_id
