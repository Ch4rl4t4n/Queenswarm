import { cockpitDynamic } from "@/lib/cockpit-dynamic-imports";

const TasksPageClient = cockpitDynamic(() =>
  import("@/components/hive/tasks-page-client").then((mod) => ({ default: mod.TasksPageClient })),
);

export const dynamic = "force-dynamic";

export default function TasksPage() {
  return <TasksPageClient />;
}
