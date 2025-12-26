"use client"

import { useState, useTransition, useEffect } from "react"
import { Button } from "@workspace/ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@workspace/ui/components/dialog"
import { Input } from "@workspace/ui/components/input"
import { updateProject } from "@/app/actions"
import type { Project } from "@/lib/db"

interface EditProjectDialogProps {
  project: Project
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function EditProjectDialog({
  project,
  open,
  onOpenChange,
}: EditProjectDialogProps) {
  const [name, setName] = useState(project.name)
  const [workingDir, setWorkingDir] = useState(project.working_dir)
  const [error, setError] = useState("")
  const [isPending, startTransition] = useTransition()

  useEffect(() => {
    setName(project.name)
    setWorkingDir(project.working_dir)
    setError("")
  }, [project])

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

    startTransition(async () => {
      const result = await updateProject(project.id, name.trim(), workingDir.trim())

      if (result.success) {
        onOpenChange(false)
      } else {
        setError(result.error || "Failed to update project")
      }
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Edit Project</DialogTitle>
            <DialogDescription>
              Update the project details for &quot;{project.name}&quot;
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <label htmlFor="edit-name" className="text-sm font-medium">
                Project Name
              </label>
              <Input
                id="edit-name"
                placeholder="Project name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={isPending}
              />
            </div>

            <div className="grid gap-2">
              <label htmlFor="edit-workingDir" className="text-sm font-medium">
                Working Directory
              </label>
              <Input
                id="edit-workingDir"
                placeholder="Working directory"
                value={workingDir}
                onChange={(e) => setWorkingDir(e.target.value)}
                disabled={isPending}
              />
            </div>

            <div className="grid gap-2 text-sm text-muted-foreground">
              <div className="flex justify-between">
                <span>Project ID:</span>
                <span className="font-mono">{project.id}</span>
              </div>
              <div className="flex justify-between">
                <span>User ID:</span>
                <span className="font-mono">{project.user_id}</span>
              </div>
              <div className="flex justify-between">
                <span>Chat ID:</span>
                <span className="font-mono">{project.chat_id}</span>
              </div>
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Updating..." : "Update Project"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
