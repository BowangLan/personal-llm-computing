"use client"

import { useState, useTransition } from "react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@workspace/ui/components/alert-dialog"
import { deleteSession } from "@/app/actions"
import type { SessionWithMessageCount } from "@/lib/db"

interface DeleteSessionDialogProps {
  session: SessionWithMessageCount
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function DeleteSessionDialog({
  session,
  open,
  onOpenChange,
}: DeleteSessionDialogProps) {
  const [error, setError] = useState("")
  const [isPending, startTransition] = useTransition()

  const handleDelete = () => {
    setError("")

    startTransition(async () => {
      const result = await deleteSession(session.id)

      if (result.success) {
        onOpenChange(false)
      } else {
        setError(result.error || "Failed to delete session")
      }
    })
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete Session</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to delete &quot;{session.name}&quot;? This
            will permanently delete the session and all {session.message_count}{" "}
            messages. This action cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>

        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        <AlertDialogFooter>
          <AlertDialogCancel disabled={isPending}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault()
              handleDelete()
            }}
            disabled={isPending}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {isPending ? "Deleting..." : "Delete"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
