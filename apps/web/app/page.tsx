import Link from "next/link"
import { Button } from "@workspace/ui/components/button"

export default function Page() {
  return (
    <div className="flex items-center justify-center min-h-svh">
      <div className="flex flex-col items-center justify-center gap-4">
        <h1 className="text-2xl font-bold">Telegram Bot Manager</h1>
        <p className="text-muted-foreground">
          Manage your Telegram bot sessions
        </p>
        <Link href="/sessions">
          <Button>View Sessions</Button>
        </Link>
      </div>
    </div>
  )
}
