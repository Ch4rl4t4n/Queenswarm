import nextDynamic from "next/dynamic";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const JobsPollConsole = nextDynamic(
  () => import("@/components/hive/jobs-poll-console").then((mod) => ({ default: mod.JobsPollConsole })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

/** Celery async workflow polling — Postgres ledger + broker snapshot. */
export default function JobsPage() {
  return <JobsPollConsole />;
}
