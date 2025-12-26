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
import { updateSession } from "@/app/actions"
import type { SessionWithMessageCount } from "@/lib/db"

interface EditSessionDialogProps {
  session: SessionWithMessageCount
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function EditSessionDialog({
  session,
  open,
  onOpenChange,
}: EditSessionDialogProps) {
  const [name, setName] = useState(session.name)
  const [error, setError] = useState("")
  const [isPending, startTransition] = useTransition()

  useEffect(() => {
    setName(session.name)
    setError("")
  }, [session])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (!name.trim()) {
      setError("Session name is required")
      return
    }

    startTransition(async () => {
      const result = await updateSession(session.id, name.trim())

      if (result.success) {
        onOpenChange(false)
      } else {
        setError(result.error || "Failed to update session")
      }
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Edit Session</DialogTitle>
            <DialogDescription>
              Update the session name for &quot;{session.name}&quot;
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <label htmlFor="edit-name" className="text-sm font-medium">
                Session Name
              </label>
              <Input
                id="edit-name"
                placeholder="Session name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={isPending}
              />
            </div>

            <div className="grid gap-2 text-sm text-muted-foreground">
              <div className="flex justify-between">
                <span>Session ID:</span>
                <span className="font-mono">{session.id}</span>
              </div>
              <div className="flex justify-between">
                <span>User ID:</span>
                <span className="font-mono">{session.user_id}</span>
              </div>
              <div className="flex justify-between">
                <span>Chat ID:</span>
                <span className="font-mono">{session.chat_id}</span>
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
              {isPending ? "Updating..." : "Update Session"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
