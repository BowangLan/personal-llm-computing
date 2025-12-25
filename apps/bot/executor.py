import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple

from observability import log_event, request_id_var, handler_var, chat_id_var

_logger = logging.getLogger("bot.executor")

@dataclass
class Task:
    id: str
    command: str
    status: str = "pending"  # pending, running, done, failed
    output: str = ""

# Track running/completed tasks
tasks: Dict[str, Task] = {}

async def run_command(command: str, timeout: int = 60) -> Tuple[str, bool]:
    """Run a shell command asynchronously."""
    t0 = time.perf_counter()
    try:
        proc = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = stdout.decode() or stderr.decode() or "(no output)"
        log_event(
            _logger,
            "command_finished",
            command=command,
            returncode=proc.returncode,
            success=proc.returncode == 0,
            output_len=len(output),
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
        return output, proc.returncode == 0
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except OSError:
            pass
        log_event(
            _logger,
            "command_timeout",
            command=command,
            timeout_s=timeout,
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
        return "Command timed out", False
    except Exception as e:
        _logger.exception(
            json.dumps(
                {"event": "command_error", "command": command, "error": str(e)},
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return f"Error: {e}", False


async def execute_parallel(commands: List[str]) -> List[Tuple[str, str, bool]]:
    """Execute multiple commands in parallel."""

    async def run_one(cmd):
        output, success = await run_command(cmd)
        return cmd, output, success

    results = await asyncio.gather(*[run_one(cmd) for cmd in commands])
    return results

async def run_background_task(task_id: str, command: str, chat_id: int, bot):
    """Run a task in background and notify when done."""
    tok_rid = request_id_var.set(f"bg-{task_id}")
    tok_h = handler_var.set("background_task")
    tok_cid = chat_id_var.set(str(chat_id))
    
    try:
        if task_id in tasks:
            tasks[task_id].status = "running"
        
        output, success = await run_command(command, timeout=300)
        
        if task_id in tasks:
            tasks[task_id].status = "done" if success else "failed"
            tasks[task_id].output = output

        status = "✅ Done" if success else "❌ Failed"
        await bot.send_message(
            chat_id,
            f"{status}: Task `{task_id}`\n`{command}`\n```\n{output[:3500]}\n```",
            parse_mode="Markdown",
        )
    except Exception:
         _logger.exception("Background task execution failed")
    finally:
        request_id_var.reset(tok_rid)
        handler_var.reset(tok_h)
        chat_id_var.reset(tok_cid)
