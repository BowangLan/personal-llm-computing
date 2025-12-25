## llm-telegram-bot

Telegram bot that:

- **Replies to normal text messages with an LLM response**
- **Runs shell commands only when you prefix your message with `run:` (or `cmd:`)**

### Environment variables

- **`BOT_TOKEN`**: Telegram bot token
- **`OPENAI_API_KEY`**: OpenAI API key (required for LLM replies)
- **`LLM_MODEL`** (optional): defaults to `gpt-5-nano`
- **`LOG_LEVEL`** (optional): logging verbosity (e.g. `DEBUG`, `INFO`, `WARNING`); defaults to `INFO`

### Usage

Run:

```bash
export BOT_TOKEN="..."
export OPENAI_API_KEY="..."
export LOG_LEVEL="INFO"  # optional
python bot.py
```

In Telegram:

- **Chat normally**: “what’s a good pasta recipe?”
- **Run commands**: `run: list files in current directory` (LLM converts to bash and executes)

### Commands

- **`/start`**: quick intro
- **`/help`**: usage
- **`/bg <command>`**: run a command in background
- **`/status`**: show last tracked tasks

