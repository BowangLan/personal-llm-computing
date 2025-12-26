"use client"

import { useState, useTransition } from "react"
import { Plus } from "lucide-react"
import { Button } from "@workspace/ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@workspace/ui/components/dialog"
import { Input } from "@workspace/ui/components/input"
import { createProject } from "@/app/actions"

export function CreateProjectDialog() {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [workingDir, setWorkingDir] = useState("")
  const [userId, setUserId] = useState("")
  const [chatId, setChatId] = useState("")
  const [error, setError] = useState("")
  const [isPending, startTransition] = useTransition()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (!name.trim()) {
      setError("Project name is required")
      return
    }

    if (!workingDir.trim()) {
      setError("Working directory is required")
      return
    }

    if (!userId.trim() || !chatId.trim()) {
      setError("User ID and Chat ID are required")
      return
    }

    const userIdNum = parseInt(userId, 10)
    const chatIdNum = parseInt(chatId, 10)

    if (isNaN(userIdNum) || isNaN(chatIdNum)) {
      setError("User ID and Chat ID must be valid numbers")
      return
    }

    startTransition(async () => {
      const result = await createProject(
        userIdNum,
        chatIdNum,
        name.trim(),
        workingDir.trim()
      )

      if (result.success) {
        setOpen(false)
        setName("")
        setWorkingDir("")
        setUserId("")
        setChatId("")
      } else {
        setError(result.error || "Failed to create project")
      }
    })
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          New Project
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Create New Project</DialogTitle>
            <DialogDescription>
              Create a new project with a working directory for the bot.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <label htmlFor="name" className="text-sm font-medium">
                Project Name
              </label>
              <Input
                id="name"
                placeholder="e.g., My App"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={isPending}
              />
            </div>

            <div className="grid gap-2">
              <label htmlFor="workingDir" className="text-sm font-medium">
                Working Directory
              </label>
              <Input
                id="workingDir"
                placeholder="e.g., /home/user/projects/my-app"
                value={workingDir}
                onChange={(e) => setWorkingDir(e.target.value)}
                disabled={isPending}
              />
            </div>

            <div className="grid gap-2">
              <label htmlFor="userId" className="text-sm font-medium">
                User ID
              </label>
              <Input
                id="userId"
                placeholder="e.g., 123456789"
                type="number"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                disabled={isPending}
              />
            </div>

            <div className="grid gap-2">
              <label htmlFor="chatId" className="text-sm font-medium">
                Chat ID
              </label>
              <Input
                id="chatId"
                placeholder="e.g., 123456789"
                type="number"
                value={chatId}
                onChange={(e) => setChatId(e.target.value)}
                disabled={isPending}
              />
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Creating..." : "Create Project"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
