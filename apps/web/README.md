# Web App - Telegram Bot Session Manager

A Next.js application for managing Telegram bot conversation sessions.

## Features

### Session Management
- **List View**: View all bot sessions in a table with:
  - Session ID, name, user ID, chat ID
  - Message count
  - Last updated timestamp
  - Quick actions (view, edit, delete)

- **Create Sessions**: Create new conversation sessions with:
  - Custom session name
  - User ID and Chat ID specification

- **Edit Sessions**: Rename existing sessions

- **Delete Sessions**: Remove sessions with confirmation dialog
  - Prevents deletion of active sessions

- **View Messages**: Browse all messages in a session
  - Shows user and assistant messages
  - Displays timestamps and message content

## Tech Stack

- **Framework**: Next.js 16 with App Router
- **UI Components**: shadcn/ui (built on Radix UI)
- **Database**: SQLite via better-sqlite3 (shared with bot)
- **Styling**: Tailwind CSS 4
- **Type Safety**: TypeScript

## Architecture

### Database Access
The web app directly accesses the bot's SQLite database located at `../bot/bot_data.db`.

- `lib/db.ts` - Database utility layer with type-safe queries
- `app/actions.ts` - Server actions for CRUD operations

### Components

**Pages:**
- `/` - Landing page with link to sessions
- `/sessions` - Main session management interface

**UI Components:**
- `SessionsTable` - Table displaying all sessions
- `CreateSessionDialog` - Dialog for creating new sessions
- `EditSessionDialog` - Dialog for renaming sessions
- `DeleteSessionDialog` - Alert dialog for session deletion
- `ViewMessagesDialog` - Dialog for viewing session messages

## Configuration

Create a `.env.local` file in `apps/web/` to configure the database path:

```bash
# Path to the bot's SQLite database
BOT_DB_PATH=/Users/bowanglan/Dev/personal-llm-computing/apps/bot/bot_data.db
```

If not set, the app will default to `../bot/bot_data.db` relative to the current working directory.

## Development

```bash
# Start development server
pnpm dev

# Type check
pnpm typecheck

# Build for production
pnpm build

# Start production server
pnpm start
```

## Troubleshooting

### better-sqlite3 Native Bindings

If you encounter an error about missing `better_sqlite3.node` bindings, rebuild the native module:

```bash
cd /Users/bowanglan/Dev/personal-llm-computing/apps/web
npm run build-release
```

Or from the project root:

```bash
pnpm rebuild better-sqlite3
```

## Database Schema

The app interacts with these tables from the bot's database:

### sessions
- `id` - Primary key
- `user_id` - Telegram user ID
- `chat_id` - Telegram chat ID
- `name` - Session name
- `state` - JSON state object
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

### messages
- `id` - Primary key
- `session_id` - Foreign key to sessions
- `user_id` - Telegram user ID
- `chat_id` - Telegram chat ID
- `role` - "user" or "assistant"
- `content` - Message text
- `timestamp` - Message timestamp

### active_sessions
- `user_id` - Telegram user ID
- `chat_id` - Telegram chat ID
- `session_id` - Currently active session ID

## Notes

- The `/sessions` page is dynamically rendered to avoid build-time database access
- Better-sqlite3 requires native bindings - run `pnpm rebuild better-sqlite3` if you encounter issues
- All timestamps are displayed relative to current time (e.g., "2 hours ago")
