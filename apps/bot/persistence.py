import json
import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

_logger = logging.getLogger("bot.persistence")

# Database file location
DB_PATH = Path(__file__).parent / "bot_data.db"


@dataclass
class Project:
    """Represents a project with a working directory."""
    id: Optional[int]
    user_id: int
    chat_id: int
    name: str
    working_dir: str
    created_at: str
    updated_at: str


@dataclass
class Session:
    """Represents a conversation session."""
    id: Optional[int]
    user_id: int
    chat_id: int
    name: str
    project_id: Optional[int]  # Optional reference to a project
    state: dict  # JSON object for session state
    created_at: str
    updated_at: str


@dataclass
class Message:
    """Represents a message in a session."""
    id: Optional[int]
    session_id: int
    user_id: int
    chat_id: int
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize database schema for session-based storage."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                working_dir TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                project_id INTEGER,
                state TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
            )
        """)

        # Migration: Add state column if it doesn't exist (for existing databases)
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in cursor.fetchall()]
        if "state" not in columns:
            cursor.execute("ALTER TABLE sessions ADD COLUMN state TEXT NOT NULL DEFAULT '{}'")
            _logger.info("Added state column to sessions table")

        # Migration: Add project_id column if it doesn't exist (for existing databases)
        if "project_id" not in columns:
            cursor.execute("ALTER TABLE sessions ADD COLUMN project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL")
            _logger.info("Added project_id column to sessions table")

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)

        # Active sessions table - tracks which session is active for each user/chat
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_sessions (
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                session_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, chat_id),
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)

        # Indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_projects_user_chat
            ON projects(user_id, chat_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user_chat
            ON sessions(user_id, chat_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_project
            ON sessions(project_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id, timestamp)
        """)

        conn.commit()
        _logger.info("Database initialized at %s", DB_PATH)


def create_session(user_id: int, chat_id: int, name: str = None, project_id: int = None) -> Session:
    """Create a new session and return it."""
    if name is None:
        name = f"Session {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

    with get_db() as conn:
        cursor = conn.cursor()
        timestamp = datetime.utcnow().isoformat()
        initial_state = "{}"

        cursor.execute(
            "INSERT INTO sessions (user_id, chat_id, name, project_id, state, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, chat_id, name, project_id, initial_state, timestamp, timestamp)
        )
        session_id = cursor.lastrowid
        conn.commit()

        _logger.info("Created session %d for user %d in chat %d (project: %s)", session_id, user_id, chat_id, project_id)
        return Session(
            id=session_id,
            user_id=user_id,
            chat_id=chat_id,
            name=name,
            project_id=project_id,
            state={},
            created_at=timestamp,
            updated_at=timestamp
        )


def get_or_create_active_session(user_id: int, chat_id: int) -> Session:
    """Get the active session for a user/chat, creating one if none exists."""
    session = get_active_session(user_id, chat_id)
    if session is None:
        # Create a new session and set it as active
        session = create_session(user_id, chat_id)
        set_active_session(user_id, chat_id, session.id)
    return session


def get_active_session(user_id: int, chat_id: int) -> Optional[Session]:
    """Get the currently active session for a user/chat."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, s.user_id, s.chat_id, s.name, s.project_id, s.state, s.created_at, s.updated_at
            FROM sessions s
            JOIN active_sessions a ON s.id = a.session_id
            WHERE a.user_id = ? AND a.chat_id = ?
        """, (user_id, chat_id))

        row = cursor.fetchone()
        if row is None:
            return None

        return Session(
            id=row["id"],
            user_id=row["user_id"],
            chat_id=row["chat_id"],
            name=row["name"],
            project_id=row["project_id"],
            state=json.loads(row["state"]) if row["state"] else {},
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


def set_active_session(user_id: int, chat_id: int, session_id: int):
    """Set the active session for a user/chat."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Verify session exists and belongs to this user/chat
        cursor.execute(
            "SELECT id FROM sessions WHERE id = ? AND user_id = ? AND chat_id = ?",
            (session_id, user_id, chat_id)
        )
        if cursor.fetchone() is None:
            raise ValueError(f"Session {session_id} not found for user {user_id} in chat {chat_id}")

        # Upsert active session
        cursor.execute("""
            INSERT INTO active_sessions (user_id, chat_id, session_id)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET session_id = ?
        """, (user_id, chat_id, session_id, session_id))

        conn.commit()
        _logger.info("Set active session to %d for user %d in chat %d", session_id, user_id, chat_id)


def list_sessions(user_id: int, chat_id: int, limit: int = None, offset: int = 0) -> List[Tuple[Session, int]]:
    """
    List sessions for a user/chat with message counts.
    Returns list of (Session, message_count) tuples, ordered by latest user message (descending).
    Sessions without user messages appear last, sorted by created_at.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT
                s.id, s.user_id, s.chat_id, s.name, s.project_id, s.state, s.created_at, s.updated_at,
                COUNT(m.id) as message_count,
                MAX(CASE WHEN m.role = 'user' THEN m.timestamp END) as last_user_message_time
            FROM sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            WHERE s.user_id = ? AND s.chat_id = ?
            GROUP BY s.id
            ORDER BY last_user_message_time DESC NULLS LAST, s.created_at DESC
        """
        params = [user_id, chat_id]

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        cursor.execute(query, params)

        rows = cursor.fetchall()
        return [
            (
                Session(
                    id=row["id"],
                    user_id=row["user_id"],
                    chat_id=row["chat_id"],
                    name=row["name"],
                    project_id=row["project_id"],
                    state=json.loads(row["state"]) if row["state"] else {},
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                ),
                row["message_count"]
            )
            for row in rows
        ]


def count_sessions(user_id: int, chat_id: int) -> int:
    """Count total sessions for a user/chat."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM sessions WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        )
        row = cursor.fetchone()
        return row["count"] if row else 0


def get_session(session_id: int) -> Optional[Session]:
    """Get a session by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, chat_id, name, project_id, state, created_at, updated_at FROM sessions WHERE id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None

        return Session(
            id=row["id"],
            user_id=row["user_id"],
            chat_id=row["chat_id"],
            name=row["name"],
            project_id=row["project_id"],
            state=json.loads(row["state"]) if row["state"] else {},
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


def update_session_state(session_id: int, state: dict):
    """Update the state of a session."""
    with get_db() as conn:
        cursor = conn.cursor()
        timestamp = datetime.utcnow().isoformat()
        state_json = json.dumps(state)
        cursor.execute(
            "UPDATE sessions SET state = ?, updated_at = ? WHERE id = ?",
            (state_json, timestamp, session_id)
        )
        conn.commit()
        _logger.info("Updated state for session %d", session_id)


def rename_session(session_id: int, new_name: str):
    """Rename a session."""
    with get_db() as conn:
        cursor = conn.cursor()
        timestamp = datetime.utcnow().isoformat()
        cursor.execute(
            "UPDATE sessions SET name = ?, updated_at = ? WHERE id = ?",
            (new_name, timestamp, session_id)
        )
        conn.commit()
        _logger.info("Renamed session %d to '%s'", session_id, new_name)


def delete_session(session_id: int):
    """Delete a session and all its messages."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        _logger.info("Deleted session %d", session_id)


def save_message(session_id: int, user_id: int, chat_id: int, role: str, content: str) -> int:
    """Save a message to a session. Returns the message ID."""
    if role not in ('user', 'assistant'):
        raise ValueError(f"Invalid role: {role}")

    with get_db() as conn:
        cursor = conn.cursor()
        timestamp = datetime.utcnow().isoformat()

        cursor.execute(
            "INSERT INTO messages (session_id, user_id, chat_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, user_id, chat_id, role, content, timestamp)
        )
        message_id = cursor.lastrowid

        # Update session's updated_at timestamp
        cursor.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (timestamp, session_id)
        )

        conn.commit()
        _logger.info("Saved %s message %d to session %d", role, message_id, session_id)
        return message_id


def get_session_messages(session_id: int, limit: int = 20) -> List[Message]:
    """
    Get recent messages from a session, ordered chronologically (oldest first).
    Returns up to `limit` most recent messages.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, session_id, user_id, chat_id, role, content, timestamp
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, limit))

        rows = cursor.fetchall()
        # Reverse to get chronological order (oldest first)
        messages = [
            Message(
                id=row["id"],
                session_id=row["session_id"],
                user_id=row["user_id"],
                chat_id=row["chat_id"],
                role=row["role"],
                content=row["content"],
                timestamp=row["timestamp"]
            )
            for row in reversed(rows)
        ]

        _logger.info("Retrieved %d messages from session %d", len(messages), session_id)
        return messages


# ============================================================================
# Project Management Functions
# ============================================================================

def create_project(user_id: int, chat_id: int, name: str, working_dir: str) -> Project:
    """Create a new project and return it."""
    with get_db() as conn:
        cursor = conn.cursor()
        timestamp = datetime.utcnow().isoformat()

        cursor.execute(
            "INSERT INTO projects (user_id, chat_id, name, working_dir, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, chat_id, name, working_dir, timestamp, timestamp)
        )
        project_id = cursor.lastrowid
        conn.commit()

        _logger.info("Created project %d for user %d in chat %d: %s -> %s", project_id, user_id, chat_id, name, working_dir)
        return Project(
            id=project_id,
            user_id=user_id,
            chat_id=chat_id,
            name=name,
            working_dir=working_dir,
            created_at=timestamp,
            updated_at=timestamp
        )


def list_projects(user_id: int, chat_id: int) -> List[Project]:
    """List all projects for a user/chat."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, chat_id, name, working_dir, created_at, updated_at FROM projects WHERE user_id = ? AND chat_id = ? ORDER BY name",
            (user_id, chat_id)
        )
        rows = cursor.fetchall()
        return [
            Project(
                id=row["id"],
                user_id=row["user_id"],
                chat_id=row["chat_id"],
                name=row["name"],
                working_dir=row["working_dir"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in rows
        ]


def get_project(project_id: int) -> Optional[Project]:
    """Get a project by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, chat_id, name, working_dir, created_at, updated_at FROM projects WHERE id = ?",
            (project_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None

        return Project(
            id=row["id"],
            user_id=row["user_id"],
            chat_id=row["chat_id"],
            name=row["name"],
            working_dir=row["working_dir"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


def update_project(project_id: int, name: str = None, working_dir: str = None):
    """Update a project's name and/or working directory."""
    with get_db() as conn:
        cursor = conn.cursor()
        timestamp = datetime.utcnow().isoformat()

        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)

        if working_dir is not None:
            updates.append("working_dir = ?")
            params.append(working_dir)

        if not updates:
            return

        updates.append("updated_at = ?")
        params.append(timestamp)
        params.append(project_id)

        query = f"UPDATE projects SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
        _logger.info("Updated project %d", project_id)


def delete_project(project_id: int):
    """Delete a project. Sessions using this project will have their project_id set to NULL."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        _logger.info("Deleted project %d", project_id)
