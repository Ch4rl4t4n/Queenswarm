import { JobsPollConsole } from "@/components/hive/jobs-poll-console";

export const dynamic = "force-dynamic";

/** Celery async workflow polling — Postgres ledger + broker snapshot. */
export default function JobsPage() {
  return <JobsPollConsole />;
}
