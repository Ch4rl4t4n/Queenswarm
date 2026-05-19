import { TasksPageClient } from "@/components/hive/tasks-page-client";

export const dynamic = "force-dynamic";

type TasksSearchParams = Record<string, string | string[] | undefined>;

function readQuery(params: TasksSearchParams): string {
  const raw = params.q;
  if (typeof raw === "string") return raw;
  if (Array.isArray(raw)) return raw[0] ?? "";
  return "";
}

export default async function TasksPage({
  searchParams,
}: {
  searchParams: Promise<TasksSearchParams>;
}) {
  const sp = await searchParams;
  return <TasksPageClient initialQuery={readQuery(sp)} />;
}
