import asyncio
import logging
import uuid

from telegram import BotCommand, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes
from telegram.constants import ParseMode

from ai import llm_reply
from config import ALLOWED_USERS
from executor import run_background_task, Task, tasks
from observability import bind_update, log_event
from persistence import (
    get_or_create_active_session,
    get_active_session,
    save_message,
    get_session_messages,
    create_session,
    set_active_session,
    list_sessions,
    count_sessions,
    rename_session,
    delete_session,
    get_session,
    update_session_state,
)

_logger = logging.getLogger("bot.handlers")


def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


async def reply_text_chunked(update: Update, text: str, *, chunk_size: int = 3500):
    """Telegram hard-limits message size; chunk replies to be safe."""
    if not text:
        await update.message.reply_text("(empty)", reply_to_message_id=update.message.message_id)
        return
    # Escape text for MarkdownV2
    escaped_text = escape_markdown_v2(text)
    for i in range(0, len(escaped_text), chunk_size):
        await update.message.reply_text(
            escaped_text[i : i + chunk_size],
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_to_message_id=update.message.message_id
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with bind_update(update, "message"):
        user_id = getattr(update.effective_user, "id", None)
        chat_id = getattr(update.effective_chat, "id", None)
        if user_id not in ALLOWED_USERS:
            log_event(
                _logger,
                "unauthorized_user",
                user_id=user_id,
                chat_id=chat_id,
            )
            return

        user_input = (update.message.text or "").strip()
        if not user_input:
            return

        log_event(
            _logger,
            "message_received",
            text_len=len(user_input),
        )

        # Send typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        # Send initial status message
        status_msg = await update.message.reply_text("⏳ Processing...")

        try:
            # Get or create active session
            await status_msg.edit_text("📂 Loading session...")
            session = get_or_create_active_session(user_id, chat_id)
            log_event(_logger, "session_loaded", session_id=session.id, session_name=session.name)

            # Load recent messages from session (last 20 messages = ~10 exchanges)
            await status_msg.edit_text("💬 Loading context...")
            past_messages = get_session_messages(session.id, limit=20)

            # Get LLM reply with past messages and session state as context
            await status_msg.edit_text("🤖 Getting LLM response...")
            reply, updated_state = await llm_reply(
                user_input,
                past_messages=past_messages,
                session_state=session.state
            )

            # Save both user message and assistant response to session
            await status_msg.edit_text("💾 Saving...")
            save_message(session.id, user_id, chat_id, "user", user_input)
            save_message(session.id, user_id, chat_id, "assistant", reply)

            # Update session state if it changed
            if updated_state != session.state:
                update_session_state(session.id, updated_state)
                log_event(_logger, "session_state_updated", session_id=session.id)

            # Delete status message before sending actual response
            await status_msg.delete()

        except Exception as e:
            _logger.exception("LLM Error")
            await status_msg.delete()
            await update.message.reply_text(f"LLM error: {e}")
            return

        await reply_text_chunked(update, reply)


async def handle_newsession(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new session and switch to it. Usage: /newsession [name]"""
    async with bind_update(update, "newsession"):
        if update.effective_user.id not in ALLOWED_USERS:
            return

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        # Get optional session name from args
        session_name = " ".join(context.args) if context.args else None

        # Create new session
        session = create_session(user_id, chat_id, session_name)
        set_active_session(user_id, chat_id, session.id)

        log_event(_logger, "new_session_created", session_id=session.id, session_name=session.name)
        await update.message.reply_text(
            f"✨ Created and switched to new session:\n`{session.name}` (ID: {session.id})",
            parse_mode="Markdown"
        )


def build_sessions_keyboard(user_id: int, chat_id: int, page: int = 0, page_size: int = 10):
    """Build inline keyboard for sessions with pagination."""
    offset = page * page_size
    sessions_with_counts = list_sessions(user_id, chat_id, limit=page_size, offset=offset)
    total_sessions = count_sessions(user_id, chat_id)
    active_session = get_active_session(user_id, chat_id)

    if not sessions_with_counts:
        return None, "No sessions found.", 0

    # Build session buttons (10 per page)
    keyboard = []
    for session, msg_count in sessions_with_counts:
        active_marker = "✓ " if active_session and session.id == active_session.id else ""
        button_text = f"{active_marker}{session.name} ({msg_count} msgs)"
        callback_data = f"session_switch:{session.id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    # Add navigation buttons on the 11th row
    total_pages = (total_sessions + page_size - 1) // page_size
    nav_buttons = []

    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"session_page:{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"session_page:{page + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Build header text
    header = f"📋 Your sessions (Page {page + 1}/{total_pages}):\n\n"
    header += "Tap a session to switch to it."

    return InlineKeyboardMarkup(keyboard), header, total_sessions


async def handle_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all sessions with pagination. Usage: /sessions"""
    async with bind_update(update, "sessions"):
        if update.effective_user.id not in ALLOWED_USERS:
            return

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        keyboard, text, total = build_sessions_keyboard(user_id, chat_id, page=0)

        if keyboard is None:
            await update.message.reply_text(text)
            return

        log_event(_logger, "sessions_listed", session_count=total)
        await update.message.reply_text(text, reply_markup=keyboard)


async def handle_switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch to a different session. Usage: /switch <session_id>"""
    async with bind_update(update, "switch"):
        if update.effective_user.id not in ALLOWED_USERS:
            return

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("Usage: /switch <session_id>")
            return

        session_id = int(context.args[0])

        try:
            # Verify session exists
            session = get_session(session_id)
            if not session or session.user_id != user_id or session.chat_id != chat_id:
                await update.message.reply_text(f"❌ Session {session_id} not found.")
                return

            set_active_session(user_id, chat_id, session_id)
            log_event(_logger, "session_switched", session_id=session_id, session_name=session.name)
            await update.message.reply_text(
                f"✓ Switched to session: `{session.name}` (ID: {session_id})",
                parse_mode="Markdown"
            )
        except ValueError as e:
            await update.message.reply_text(f"❌ Error: {e}")


async def handle_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rename a session. Usage: /rename <session_id> <new_name>"""
    async with bind_update(update, "rename"):
        if update.effective_user.id not in ALLOWED_USERS:
            return

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if len(context.args) < 2 or not context.args[0].isdigit():
            await update.message.reply_text("Usage: /rename <session_id> <new_name>")
            return

        session_id = int(context.args[0])
        new_name = " ".join(context.args[1:])

        # Verify session exists and belongs to user
        session = get_session(session_id)
        if not session or session.user_id != user_id or session.chat_id != chat_id:
            await update.message.reply_text(f"❌ Session {session_id} not found.")
            return

        rename_session(session_id, new_name)
        log_event(_logger, "session_renamed", session_id=session_id, new_name=new_name)
        await update.message.reply_text(
            f"✓ Renamed session {session_id} to: `{new_name}`",
            parse_mode="Markdown"
        )


async def handle_delsession(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a session. Usage: /delsession <session_id>"""
    async with bind_update(update, "delsession"):
        if update.effective_user.id not in ALLOWED_USERS:
            return

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("Usage: /delsession <session_id>")
            return

        session_id = int(context.args[0])

        # Verify session exists and belongs to user
        session = get_session(session_id)
        if not session or session.user_id != user_id or session.chat_id != chat_id:
            await update.message.reply_text(f"❌ Session {session_id} not found.")
            return

        # Check if it's the active session
        active_session = get_active_session(user_id, chat_id)
        if active_session and active_session.id == session_id:
            await update.message.reply_text("❌ Cannot delete active session. Switch to another session first.")
            return

        delete_session(session_id)
        log_event(_logger, "session_deleted", session_id=session_id)
        await update.message.reply_text(f"✓ Deleted session {session_id}")


async def handle_background(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /bg <command> - runs in background, notifies when done."""
    async with bind_update(update, "bg"):
        if update.effective_user.id not in ALLOWED_USERS:
            return

        # context.args comes from CommandHandler
        command = " ".join(context.args)
        if not command:
            await update.message.reply_text("Usage: /bg <command>")
            return

        task_id = str(uuid.uuid4())[:8]
        tasks[task_id] = Task(id=task_id, command=command)

        log_event(_logger, "background_task_started", task_id=task_id, command=command)
        await update.message.reply_text(f"Started background task `{task_id}`")

        # Fire and forget - runs independently
        asyncio.create_task(
            run_background_task(task_id, command, update.effective_chat.id, context.bot)
        )


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check status of running tasks."""
    async with bind_update(update, "status"):
        if update.effective_user.id not in ALLOWED_USERS:
            return

        if not tasks:
            await update.message.reply_text("No tasks tracked.")
            return

        lines = []
        for t in list(tasks.values())[-10:]:  # Last 10
            icon = {"pending": "⏳", "running": "🔄", "done": "✅", "failed": "❌"}
            lines.append(f"{icon.get(t.status, '?')} `{t.id}` - {t.command[:40]}")

        log_event(_logger, "status_requested", task_count=len(tasks))
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with bind_update(update, "start"):
        if update.effective_user.id not in ALLOWED_USERS:
            return
        await update.message.reply_text(
            "Hi! Send messages to chat with the LLM.\n\n"
            "Session management:\n"
            "- /sessions — list all sessions\n"
            "- /newsession [name] — create new session\n"
            "- /switch <id> — switch to session\n"
            "- /rename <id> <name> — rename session\n"
            "- /delsession <id> — delete session\n\n"
            "Other commands:\n"
            "- /bg <command> — run command in background\n"
            "- /status — show background tasks",
            parse_mode="Markdown",
        )


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with bind_update(update, "help"):
        if update.effective_user.id not in ALLOWED_USERS:
            return
        await update.message.reply_text(
            "Usage:\n"
            "- Send messages to chat with the LLM.\n"
            "- Each conversation is organized into sessions.\n\n"
            "Session management:\n"
            "- /sessions — list all sessions\n"
            "- /newsession [name] — create new session\n"
            "- /switch <id> — switch to session\n"
            "- /rename <id> <name> — rename session\n"
            "- /delsession <id> — delete session\n\n"
            "Other commands:\n"
            "- /bg <command> — run command in background\n"
            "- /status — show background tasks",
            parse_mode="Markdown",
        )


async def handle_session_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks for session navigation and switching."""
    query = update.callback_query
    await query.answer()

    if update.effective_user.id not in ALLOWED_USERS:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    data = query.data

    try:
        if data.startswith("session_page:"):
            # Handle pagination
            page = int(data.split(":")[1])
            keyboard, text, _ = build_sessions_keyboard(user_id, chat_id, page=page)

            if keyboard is None:
                await query.edit_message_text(text)
                return

            await query.edit_message_text(text, reply_markup=keyboard)
            log_event(_logger, "sessions_page_changed", page=page)

        elif data.startswith("session_switch:"):
            # Handle session switching
            session_id = int(data.split(":")[1])

            # Verify session exists
            session = get_session(session_id)
            if not session or session.user_id != user_id or session.chat_id != chat_id:
                await query.edit_message_text(f"❌ Session {session_id} not found.")
                return

            set_active_session(user_id, chat_id, session_id)
            log_event(_logger, "session_switched", session_id=session_id, session_name=session.name)

            # Update the message to show the new active session
            # Extract current page from callback query message if possible, default to 0
            page = 0
            keyboard, text, _ = build_sessions_keyboard(user_id, chat_id, page=page)

            if keyboard:
                success_text = f"✓ Switched to: {session.name}\n\n{text}"
                await query.edit_message_text(success_text, reply_markup=keyboard)
            else:
                await query.edit_message_text(f"✓ Switched to session: `{session.name}` (ID: {session_id})", parse_mode="Markdown")

    except Exception as e:
        _logger.exception("Error handling session callback")
        await query.edit_message_text(f"❌ Error: {e}")


async def post_init(application: Application) -> None:
    # Configure the Telegram client-side command menu.
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Show quick intro"),
            BotCommand("help", "Show help / usage"),
            BotCommand("sessions", "List all sessions"),
            BotCommand("newsession", "Create a new session"),
            BotCommand("switch", "Switch to a session"),
            BotCommand("rename", "Rename a session"),
            BotCommand("delsession", "Delete a session"),
            BotCommand("bg", "Run a command in background"),
            BotCommand("status", "Show last tracked tasks"),
        ]
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    # PTB global error handler for unhandled exceptions.
    try:
        upd = update if isinstance(update, Update) else None
        if upd is not None:
            async with bind_update(upd, "error"):
                _logger.exception("Unhandled exception", exc_info=context.error)
        else:
            _logger.exception("Unhandled exception (no update)", exc_info=context.error)
    except Exception:
        # Avoid recursive error loops.
        logging.getLogger("bot").exception('{"event":"error_handler_failed"}')
