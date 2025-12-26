import { getProjects } from "@/app/actions"
import { ProjectsTable } from "@/components/projects-table"
import { CreateProjectDialog } from "@/components/create-project-dialog"

export const dynamic = "force-dynamic"

export default async function ProjectsPage() {
  const result = await getProjects()

  if (!result.success) {
    return (
      <div className="container mx-auto py-10">
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">
            Error loading projects: {result.error}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-10">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
          <p className="text-muted-foreground mt-2">
            Manage your bot projects and working directories
          </p>
        </div>
        <CreateProjectDialog />
      </div>

      <ProjectsTable projects={result.data || []} />
    </div>
  )
}
