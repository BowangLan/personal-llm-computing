import { getSessions } from "@/app/actions"
import { SessionsTable } from "@/components/sessions-table"
import { CreateSessionDialog } from "@/components/create-session-dialog"

export const dynamic = "force-dynamic"

export default async function SessionsPage() {
  const result = await getSessions()

  if (!result.success) {
    return (
      <div className="container mx-auto py-10">
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">
            Error loading sessions: {result.error}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-10">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Sessions</h1>
          <p className="text-muted-foreground mt-2">
            Manage your Telegram bot conversation sessions
          </p>
        </div>
        <CreateSessionDialog />
      </div>

      <SessionsTable sessions={result.data || []} />
    </div>
  )
}
