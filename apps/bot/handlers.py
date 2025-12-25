import asyncio
import logging
import uuid
import json

from telegram import BotCommand, Update
from telegram.ext import Application, ContextTypes

from ai import llm_reply, parse_commands
from config import ALLOWED_USERS
from executor import execute_parallel, run_background_task, Task, tasks
from observability import bind_update, log_event

_logger = logging.getLogger("bot.handlers")


async def reply_text_chunked(update: Update, text: str, *, chunk_size: int = 3500):
    """Telegram hard-limits message size; chunk replies to be safe."""
    if not text:
        await update.message.reply_text("(empty)")
        return
    for i in range(0, len(text), chunk_size):
        await update.message.reply_text(text[i : i + chunk_size])


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
            is_run=user_input.lower().startswith(("run:", "cmd:")),
        )

        
        lower = user_input.lower()
        if lower.startswith("run:") or lower.startswith("cmd:"):
            command_request = user_input.split(":", 1)[1].strip()
            commands = await parse_commands(command_request)

            if not commands:
                await update.message.reply_text(
                    "Couldn't parse that into safe commands. Try rephrasing, or be more specific."
                )
                return

            log_event(_logger, "commands_execute_start", count=len(commands))

            if len(commands) > 1:
                cmd_list = "\n".join(f"  • {c}" for c in commands)
                await update.message.reply_text(
                    f"Running {len(commands)} tasks:\n{cmd_list}"
                )

            results = await execute_parallel(commands)

            for cmd, output, success in results:
                status = "✅" if success else "❌"
                msg = f"{status} `{cmd}`\n```\n{output[:3500]}\n```"
                await update.message.reply_text(msg, parse_mode="Markdown")
            return

        try:
            reply = await llm_reply(user_input)
        except Exception as e:
            _logger.exception("LLM Error")
            await update.message.reply_text(f"LLM error: {e}")
            return

        await reply_text_chunked(update, reply)


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
            "Hi! Send normal messages to chat with the LLM.\n"
            "To run shell commands, prefix your message with `run:` (or `cmd:`).\n\n"
            "Commands:\n"
            "- /bg <command> — run a command in background\n"
            "- /status — show last tracked tasks",
            parse_mode="Markdown",
        )


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with bind_update(update, "help"):
        if update.effective_user.id not in ALLOWED_USERS:
            return
        await update.message.reply_text(
            "Usage:\n"
            "- Chat normally to get an LLM response.\n"
            "- Prefix with `run:` (or `cmd:`) to execute shell commands.\n\n"
            "Commands:\n"
            "- /bg <command>\n"
            "- /status",
            parse_mode="Markdown",
        )


async def post_init(application: Application) -> None:
    # Configure the Telegram client-side command menu.
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Show quick intro"),
            BotCommand("help", "Show help / usage"),
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
