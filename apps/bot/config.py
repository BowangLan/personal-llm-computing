import os

# Parse comma-separated user IDs from environment or use default
_allowed_users_env = os.getenv("ALLOWED_USERS", "2073351216")
ALLOWED_USERS = [int(uid.strip()) for uid in _allowed_users_env.split(",") if uid.strip()]

BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
