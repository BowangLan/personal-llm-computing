import Database from "better-sqlite3"
import { resolve } from "path"

// Path to the bot's database
// Use environment variable if set, otherwise resolve relative to project root
const DB_PATH =
  process.env.BOT_DB_PATH ||
  resolve(process.cwd(), "../bot/bot_data.db")

export interface Session {
  id: number
  user_id: number
  chat_id: number
  name: string
  state: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: number
  session_id: number
  user_id: number
  chat_id: number
  role: "user" | "assistant"
  content: string
  timestamp: string
}

export interface SessionWithMessageCount extends Session {
  message_count: number
}

let db: Database.Database | null = null

function getDb() {
  if (!db) {
    db = new Database(DB_PATH)
    db.pragma("journal_mode = WAL")
  }
  return db
}

export function getAllSessions(): SessionWithMessageCount[] {
  const database = getDb()
  const stmt = database.prepare(`
    SELECT
      s.id, s.user_id, s.chat_id, s.name, s.state, s.created_at, s.updated_at,
      COUNT(m.id) as message_count
    FROM sessions s
    LEFT JOIN messages m ON s.id = m.session_id
    GROUP BY s.id
    ORDER BY s.updated_at DESC
  `)

  return stmt.all() as SessionWithMessageCount[]
}

export function getSession(id: number): Session | undefined {
  const database = getDb()
  const stmt = database.prepare(`
    SELECT id, user_id, chat_id, name, state, created_at, updated_at
    FROM sessions
    WHERE id = ?
  `)

  return stmt.get(id) as Session | undefined
}

export function createSession(
  userId: number,
  chatId: number,
  name: string
): Session {
  const database = getDb()
  const timestamp = new Date().toISOString()
  const state = "{}"

  const stmt = database.prepare(`
    INSERT INTO sessions (user_id, chat_id, name, state, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `)

  const info = stmt.run(userId, chatId, name, state, timestamp, timestamp)

  return {
    id: info.lastInsertRowid as number,
    user_id: userId,
    chat_id: chatId,
    name,
    state,
    created_at: timestamp,
    updated_at: timestamp,
  }
}

export function updateSession(
  id: number,
  name: string
): { success: boolean; error?: string } {
  const database = getDb()
  const timestamp = new Date().toISOString()

  try {
    const stmt = database.prepare(`
      UPDATE sessions
      SET name = ?, updated_at = ?
      WHERE id = ?
    `)

    const info = stmt.run(name, timestamp, id)

    return {
      success: info.changes > 0,
      error: info.changes === 0 ? "Session not found" : undefined,
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error",
    }
  }
}

export function deleteSession(id: number): {
  success: boolean
  error?: string
} {
  const database = getDb()

  try {
    // Check if session is active
    const activeStmt = database.prepare(`
      SELECT session_id FROM active_sessions WHERE session_id = ?
    `)
    const active = activeStmt.get(id)

    if (active) {
      return {
        success: false,
        error: "Cannot delete active session. Switch to another session first.",
      }
    }

    const stmt = database.prepare("DELETE FROM sessions WHERE id = ?")
    const info = stmt.run(id)

    return {
      success: info.changes > 0,
      error: info.changes === 0 ? "Session not found" : undefined,
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error",
    }
  }
}

export function getSessionMessages(sessionId: number): Message[] {
  const database = getDb()
  const stmt = database.prepare(`
    SELECT id, session_id, user_id, chat_id, role, content, timestamp
    FROM messages
    WHERE session_id = ?
    ORDER BY timestamp ASC
  `)

  return stmt.all(sessionId) as Message[]
}
