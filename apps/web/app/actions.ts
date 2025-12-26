"use server"

import { revalidatePath } from "next/cache"
import {
  getAllSessions,
  getSession,
  createSession as dbCreateSession,
  updateSession as dbUpdateSession,
  deleteSession as dbDeleteSession,
  getSessionMessages,
  getAllProjects,
  getProject,
  createProject as dbCreateProject,
  updateProject as dbUpdateProject,
  deleteProject as dbDeleteProject,
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
  name: string,
  projectId?: number | null
) {
  try {
    const session = dbCreateSession(userId, chatId, name, projectId)
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

export async function updateSession(
  id: number,
  name: string,
  projectId?: number | null
) {
  try {
    const result = dbUpdateSession(id, name, projectId)
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

// ============================================================================
// Project Actions
// ============================================================================

export async function getProjects() {
  try {
    const projects = getAllProjects()
    return { success: true, data: projects }
  } catch (error) {
    console.error("Error fetching projects:", error)
    return {
      success: false,
      error: error instanceof Error ? error.message : "Failed to fetch projects",
    }
  }
}

export async function getProjectById(id: number) {
  try {
    const project = getProject(id)
    if (!project) {
      return { success: false, error: "Project not found" }
    }
    return { success: true, data: project }
  } catch (error) {
    console.error("Error fetching project:", error)
    return {
      success: false,
      error: error instanceof Error ? error.message : "Failed to fetch project",
    }
  }
}

export async function createProject(
  userId: number,
  chatId: number,
  name: string,
  workingDir: string
) {
  try {
    const project = dbCreateProject(userId, chatId, name, workingDir)
    revalidatePath("/projects")
    return { success: true, data: project }
  } catch (error) {
    console.error("Error creating project:", error)
    return {
      success: false,
      error: error instanceof Error ? error.message : "Failed to create project",
    }
  }
}

export async function updateProject(
  id: number,
  name: string,
  workingDir: string
) {
  try {
    const result = dbUpdateProject(id, name, workingDir)
    if (result.success) {
      revalidatePath("/projects")
    }
    return result
  } catch (error) {
    console.error("Error updating project:", error)
    return {
      success: false,
      error: error instanceof Error ? error.message : "Failed to update project",
    }
  }
}

export async function deleteProject(id: number) {
  try {
    const result = dbDeleteProject(id)
    if (result.success) {
      revalidatePath("/projects")
    }
    return result
  } catch (error) {
    console.error("Error deleting project:", error)
    return {
      success: false,
      error: error instanceof Error ? error.message : "Failed to delete project",
    }
  }
}
