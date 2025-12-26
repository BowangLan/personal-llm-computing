"use client"

import { useState } from "react"
import { formatDistanceToNow } from "date-fns"
import { Pencil, Trash2, MessageSquare } from "lucide-react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"
import { Button } from "@workspace/ui/components/button"
import { Badge } from "@workspace/ui/components/badge"
import type { SessionWithMessageCount } from "@/lib/db"
import { EditSessionDialog } from "./edit-session-dialog"
import { DeleteSessionDialog } from "./delete-session-dialog"
import { ViewMessagesDialog } from "./view-messages-dialog"

interface SessionsTableProps {
  sessions: SessionWithMessageCount[]
}

export function SessionsTable({ sessions }: SessionsTableProps) {
  const [editingSession, setEditingSession] =
    useState<SessionWithMessageCount | null>(null)
  const [deletingSession, setDeletingSession] =
    useState<SessionWithMessageCount | null>(null)
  const [viewingSession, setViewingSession] =
    useState<SessionWithMessageCount | null>(null)

  if (sessions.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-8 text-center">
        <p className="text-muted-foreground">
          No sessions found. Create your first session to get started.
        </p>
      </div>
    )
  }

  return (
    <>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[100px]">ID</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>User ID</TableHead>
              <TableHead>Chat ID</TableHead>
              <TableHead>Messages</TableHead>
              <TableHead>Last Updated</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sessions.map((session) => (
              <TableRow key={session.id}>
                <TableCell className="font-mono">{session.id}</TableCell>
                <TableCell className="font-medium">{session.name}</TableCell>
                <TableCell className="font-mono">{session.user_id}</TableCell>
                <TableCell className="font-mono">{session.chat_id}</TableCell>
                <TableCell>
                  <Badge variant="secondary">
                    {session.message_count} messages
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {formatDistanceToNow(new Date(session.updated_at), {
                    addSuffix: true,
                  })}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setViewingSession(session)}
                      title="View messages"
                    >
                      <MessageSquare className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditingSession(session)}
                      title="Edit session"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDeletingSession(session)}
                      title="Delete session"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {editingSession && (
        <EditSessionDialog
          session={editingSession}
          open={!!editingSession}
          onOpenChange={(open) => !open && setEditingSession(null)}
        />
      )}

      {deletingSession && (
        <DeleteSessionDialog
          session={deletingSession}
          open={!!deletingSession}
          onOpenChange={(open) => !open && setDeletingSession(null)}
        />
      )}

      {viewingSession && (
        <ViewMessagesDialog
          session={viewingSession}
          open={!!viewingSession}
          onOpenChange={(open) => !open && setViewingSession(null)}
        />
      )}
    </>
  )
}
