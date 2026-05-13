"use client";

import { hivePostJson } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useState } from "react";

interface AgentDetailRunNowProps {
  agentId: string;
}

/** Queues a universal bee run via cookie-authenticated hive proxy then routes to backlog. */
export function AgentDetailRunNow({ agentId }: AgentDetailRunNowProps): JSX.Element {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function run(): Promise<void> {
    setBusy(true);
    try {
      const payload = await hivePostJson<{ task_id: string }>(`agents/${encodeURIComponent(agentId)}/run`, {});
      if (payload?.task_id) {
        router.push("/tasks");
      }
    } catch {
      /* errors bubble via alerts for now */
      window.alert("Run failed — check session and celery worker.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      disabled={busy}
      onClick={() => void run()}
      className="rounded-lg bg-data/10 px-4 py-2 font-[family-name:var(--font-poppins)] text-sm text-data transition hover:bg-data/20 disabled:opacity-45 border border-data/35"
    >
      {busy ? "Queuing…" : "▶ Run now"}
    </button>
  );
}
