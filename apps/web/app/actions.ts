"use server"

import { revalidatePath } from "next/cache"
import {
  getAllSessions,
  getSession,
  createSession as dbCreateSession,
  updateSession as dbUpdateSession,
  deleteSession as dbDeleteSession,
  getSessionMessages,
} from "@/lib/db"

export async function getSessions() {
  try {
    const sessions = getAllSessions()
    return { success: true, data: sessions }
  } catch (error) {
    console.error("Error fetching sessions:", error)
    return {
      success: false,
      error: error instanceof Error ? error.message : "Failed to fetch sessions",
    }
  }
}

export async function getSessionById(id: number) {
  try {
    const session = getSession(id)
    if (!session) {
      return { success: false, error: "Session not found" }
    }
    return { success: true, data: session }
  } catch (error) {
    console.error("Error fetching session:", error)
    return {
      success: false,
      error: error instanceof Error ? error.message : "Failed to fetch session",
    }
  }
}

export async function getMessages(sessionId: number) {
  try {
    const messages = getSessionMessages(sessionId)
    return { success: true, data: messages }
  } catch (error) {
    console.error("Error fetching messages:", error)
    return {
      success: false,
      error: error instanceof Error ? error.message : "Failed to fetch messages",
    }
  }
}

export async function createSession(
  userId: number,
  chatId: number,
  name: string
) {
  try {
    const session = dbCreateSession(userId, chatId, name)
    revalidatePath("/sessions")
    return { success: true, data: session }
  } catch (error) {
    console.error("Error creating session:", error)
    return {
      success: false,
      error: error instanceof Error ? error.message : "Failed to create session",
    }
  }
}

export async function updateSession(id: number, name: string) {
  try {
    const result = dbUpdateSession(id, name)
    if (result.success) {
      revalidatePath("/sessions")
    }
    return result
  } catch (error) {
    console.error("Error updating session:", error)
    return {
      success: false,
      error: error instanceof Error ? error.message : "Failed to update session",
    }
  }
}

export async function deleteSession(id: number) {
  try {
    const result = dbDeleteSession(id)
    if (result.success) {
      revalidatePath("/sessions")
    }
    return result
  } catch (error) {
    console.error("Error deleting session:", error)
    return {
      success: false,
      error: error instanceof Error ? error.message : "Failed to delete session",
    }
  }
}
