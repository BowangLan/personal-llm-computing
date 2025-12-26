"use client"

import { useEffect, useState } from "react"
import { formatDistanceToNow } from "date-fns"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@workspace/ui/components/dialog"
import { Badge } from "@workspace/ui/components/badge"
import { getMessages } from "@/app/actions"
import type { SessionWithMessageCount, Message } from "@/lib/db"

interface ViewMessagesDialogProps {
  session: SessionWithMessageCount
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ViewMessagesDialog({
  session,
  open,
  onOpenChange,
}: ViewMessagesDialogProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    if (open) {
      setLoading(true)
      setError("")

      getMessages(session.id)
        .then((result) => {
          if (result.success && result.data) {
            setMessages(result.data)
          } else {
            setError(result.error || "Failed to load messages")
          }
        })
        .finally(() => {
          setLoading(false)
        })
    }
  }, [session.id, open])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Messages</DialogTitle>
          <DialogDescription>
            Viewing messages for &quot;{session.name}&quot;
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-4 py-4">
          {loading && (
            <div className="text-center text-muted-foreground">
              Loading messages...
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          {!loading && !error && messages.length === 0 && (
            <div className="text-center text-muted-foreground">
              No messages in this session yet.
            </div>
          )}

          {!loading &&
            !error &&
            messages.map((message) => (
              <div
                key={message.id}
                className={`rounded-lg border p-4 ${
                  message.role === "user"
                    ? "bg-muted/50"
                    : "bg-primary/5"
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Badge
                    variant={message.role === "user" ? "default" : "secondary"}
                  >
                    {message.role === "user" ? "User" : "Assistant"}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(message.timestamp), {
                      addSuffix: true,
                    })}
                  </span>
                </div>
                <p className="text-sm whitespace-pre-wrap break-words">
                  {message.content}
                </p>
              </div>
            ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
