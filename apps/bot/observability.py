import contextvars
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Optional

from telegram import Update

from config import LOG_LEVEL, ERROR_LOG_FILE

# ---- Context Vars ----
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id", default="-")
chat_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("chat_id", default="-")
handler_var: contextvars.ContextVar[str] = contextvars.ContextVar("handler", default="-")


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        record.chat_id = chat_id_var.get()
        record.handler = handler_var.get()
        return True


def configure_logging() -> None:
    level = getattr(logging, LOG_LEVEL, logging.INFO)

    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return

    handler: logging.Handler
    try:
        from rich.logging import RichHandler
        from rich.traceback import install as rich_traceback_install

        rich_traceback_install(show_locals=False)
        handler = RichHandler(
            rich_tracebacks=True,
            tracebacks_show_locals=False,
            show_path=False,
        )
    except ImportError:
        handler = logging.StreamHandler()

    handler.setLevel(level)
    handler.addFilter(ContextFilter())
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s "
            "[rid=%(request_id)s uid=%(user_id)s cid=%(chat_id)s h=%(handler)s] %(message)s"
        )
    )

    root.setLevel(level)
    root.addHandler(handler)

    # Add file handler for errors
    file_handler = logging.FileHandler(ERROR_LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.ERROR)
    file_handler.addFilter(ContextFilter())
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s "
            "[rid=%(request_id)s uid=%(user_id)s cid=%(chat_id)s h=%(handler)s] %(message)s"
        )
    )
    root.addHandler(file_handler)


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


@asynccontextmanager
async def bind_update(update: Update, handler_name: str):
    t0 = time.perf_counter()
    # Handle cases where update might not handle these attributes gracefully or might be None
    upd_id = getattr(update, 'update_id', '-')
    user_id = getattr(update.effective_user, "id", "-")
    chat_id = getattr(update.effective_chat, "id", "-")

    tok_rid = request_id_var.set(f"upd-{upd_id}")
    tok_uid = user_id_var.set(str(user_id))
    tok_cid = chat_id_var.set(str(chat_id))
    tok_h = handler_var.set(handler_name)
    try:
        yield
    finally:
        request_id_var.reset(tok_rid)
        user_id_var.reset(tok_uid)
        chat_id_var.reset(tok_cid)
        handler_var.reset(tok_h)
        logging.getLogger("bot").debug(
            json.dumps(
                {
                    "event": "handler_finished",
                    "duration_ms": int((time.perf_counter() - t0) * 1000),
                },
                separators=(",", ":"),
            )
        )

def get_logger(name: str = "bot") -> logging.Logger:
    return logging.getLogger(name)
