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


async def llm_reply(user_input: str, past_messages: List[Message] = None, session_state: dict = None) -> tuple[str, dict]:
    """
    General chat response for normal text messages.
    Uses past messages from the active session as context.
    Returns (response, updated_state) tuple.
    """
    t0 = time.perf_counter()

    if session_state is None:
        session_state = {}

    # Build conversation history from past messages
    conversation_history = ""
    if past_messages:
        history_lines = []
        for msg in past_messages:
            role = "User" if msg.role == "user" else "Assistant"
            # Truncate very long messages for context (keep last 500 chars)
            content = msg.content[-500:] if len(msg.content) > 500 else msg.content
            history_lines.append(f"{role}: {content}")
        conversation_history = "\n\nPrevious conversation:\n" + "\n".join(history_lines) + "\n"

    # Format session state for prompt
    state_section = f"\n\nCurrent session state: {json.dumps(session_state, indent=2)}\n"

    prompt = f"""You are a helpful assistant in a Telegram chat.
Answer clearly and concisely.
If the user asks you to run shell commands, tell them to prefix with 'run:' and describe what will happen.
{conversation_history}{state_section}
IMPORTANT: You have access to a session state object that persists across messages in this conversation.
You can modify this state in any way you want to keep track of information, context, or anything else you find useful.
Use it as a memory sink for the session. Update it with relevant information from the conversation.

User message: {user_input}"""

    schema = {
        "type": "object",
        "properties": {
            "response": {
                "type": "string",
                "description": "The chat response to the user"
            },
            "updated_state": {
                "type": "object",
                "description": "Updated session state. You can modify this however you want to track information across the conversation. Can be any valid JSON object."
            }
        },
        "required": ["response", "updated_state"]
    }

    result = None
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Bash", "Glob", "WebSearch", "WebFetch"],
            output_format={"type": "json_schema", "schema": schema}
        ),
    ):
        if hasattr(message, "structured_output"):
            result = message.structured_output

    reply = result.get("response", "(empty response)") if result else "(empty response)"
    updated_state = result.get("updated_state", session_state) if result else session_state

    log_event(
        _logger,
        "llm_reply_finished",
        input_len=len(user_input),
        output_len=len(reply),
        context_count=len(past_messages) if past_messages else 0,
        state_updated=updated_state != session_state,
        duration_ms=int((time.perf_counter() - t0) * 1000),
    )
    return reply, updated_state
