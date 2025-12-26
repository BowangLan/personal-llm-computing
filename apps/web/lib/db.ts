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
  project_id: number | null
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

export interface Project {
  id: number
  user_id: number
  chat_id: number
  name: string
  working_dir: string
  created_at: string
  updated_at: string
}

export interface SessionWithMessageCount extends Session {
  message_count: number
  project_name?: string
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
      s.id, s.user_id, s.chat_id, s.name, s.project_id, s.state, s.created_at, s.updated_at,
      COUNT(m.id) as message_count,
      p.name as project_name
    FROM sessions s
    LEFT JOIN messages m ON s.id = m.session_id
    LEFT JOIN projects p ON s.project_id = p.id
    GROUP BY s.id
    ORDER BY s.updated_at DESC
  `)

  return stmt.all() as SessionWithMessageCount[]
}

export function getSession(id: number): Session | undefined {
  const database = getDb()
  const stmt = database.prepare(`
    SELECT id, user_id, chat_id, name, project_id, state, created_at, updated_at
    FROM sessions
    WHERE id = ?
  `)

  return stmt.get(id) as Session | undefined
}

export function createSession(
  userId: number,
  chatId: number,
  name: string,
  projectId?: number | null
): Session {
  const database = getDb()
  const timestamp = new Date().toISOString()
  const state = "{}"

  const stmt = database.prepare(`
    INSERT INTO sessions (user_id, chat_id, name, project_id, state, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `)

  const info = stmt.run(
    userId,
    chatId,
    name,
    projectId ?? null,
    state,
    timestamp,
    timestamp
  )

  return {
    id: info.lastInsertRowid as number,
    user_id: userId,
    chat_id: chatId,
    name,
    project_id: projectId ?? null,
    state,
    created_at: timestamp,
    updated_at: timestamp,
  }
}

export function updateSession(
  id: number,
  name: string,
  projectId?: number | null
): { success: boolean; error?: string } {
  const database = getDb()
  const timestamp = new Date().toISOString()

  try {
    const stmt = database.prepare(`
      UPDATE sessions
      SET name = ?, project_id = ?, updated_at = ?
      WHERE id = ?
    `)

    const info = stmt.run(name, projectId ?? null, timestamp, id)

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

// ============================================================================
// Project Management Functions
// ============================================================================

export function getAllProjects(): Project[] {
  const database = getDb()
  const stmt = database.prepare(`
    SELECT id, user_id, chat_id, name, working_dir, created_at, updated_at
    FROM projects
    ORDER BY name ASC
  `)

  return stmt.all() as Project[]
}

export function getProject(id: number): Project | undefined {
  const database = getDb()
  const stmt = database.prepare(`
    SELECT id, user_id, chat_id, name, working_dir, created_at, updated_at
    FROM projects
    WHERE id = ?
  `)

  return stmt.get(id) as Project | undefined
}

export function createProject(
  userId: number,
  chatId: number,
  name: string,
  workingDir: string
): Project {
  const database = getDb()
  const timestamp = new Date().toISOString()

  const stmt = database.prepare(`
    INSERT INTO projects (user_id, chat_id, name, working_dir, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `)

  const info = stmt.run(userId, chatId, name, workingDir, timestamp, timestamp)

  return {
    id: info.lastInsertRowid as number,
    user_id: userId,
    chat_id: chatId,
    name,
    working_dir: workingDir,
    created_at: timestamp,
    updated_at: timestamp,
  }
}

export function updateProject(
  id: number,
  name: string,
  workingDir: string
): { success: boolean; error?: string } {
  const database = getDb()
  const timestamp = new Date().toISOString()

  try {
    const stmt = database.prepare(`
      UPDATE projects
      SET name = ?, working_dir = ?, updated_at = ?
      WHERE id = ?
    `)

    const info = stmt.run(name, workingDir, timestamp, id)

    return {
      success: info.changes > 0,
      error: info.changes === 0 ? "Project not found" : undefined,
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error",
    }
  }
}

export function deleteProject(id: number): {
  success: boolean
  error?: string
} {
  const database = getDb()

  try {
    // Check if any sessions are using this project
    const sessionCheckStmt = database.prepare(`
      SELECT COUNT(*) as count FROM sessions WHERE project_id = ?
    `)
    const result = sessionCheckStmt.get(id) as { count: number }

    if (result.count > 0) {
      return {
        success: false,
        error: `Cannot delete project. ${result.count} session(s) are using it.`,
      }
    }

    const stmt = database.prepare("DELETE FROM projects WHERE id = ?")
    const info = stmt.run(id)

    return {
      success: info.changes > 0,
      error: info.changes === 0 ? "Project not found" : undefined,
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error",
    }
  }
}
