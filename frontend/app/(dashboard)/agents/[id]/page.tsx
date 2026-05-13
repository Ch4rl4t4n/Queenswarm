import Link from "next/link";
import { notFound } from "next/navigation";

import { AgentDetailRunNow } from "@/components/hive/agent-detail-run-now";
import { AgentRemoteControls } from "@/components/hive/agent-remote-controls";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { hiveServerJson, hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow, TaskRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

interface AgentDetailPageProps {
  params: Promise<{ id: string }>;
}

interface AgentConfigPreview {
  schedule_value?: string | null;
  is_active?: boolean;
  last_run_result?: Record<string, unknown> | string | null;
  last_run_at?: string | null;
  run_count?: number;
}

export default async function AgentDetailPage(props: AgentDetailPageProps) {
  const { id } = await props.params;
  const agent = await hiveServerRawJson<AgentRow>(`/agents/${encodeURIComponent(id)}`);
  const recentTasks = await hiveServerRawJson<TaskRow[]>(
    `/tasks?agent_id=${encodeURIComponent(id)}&limit=50`,
  );

  let beeCfg: AgentConfigPreview | null = null;
  try {
    beeCfg = await hiveServerJson<AgentConfigPreview>(`/agents/${encodeURIComponent(id)}/config`);
  } catch {
    beeCfg = null;
  }

  if (!agent) {
    notFound();
  }

  const tasks = recentTasks ?? [];
  let lastSnippet = "";
  if (beeCfg?.last_run_result) {
    lastSnippet =
      typeof beeCfg.last_run_result === "string"
        ? beeCfg.last_run_result.slice(0, 680)
        : JSON.stringify(beeCfg.last_run_result, null, 2).slice(0, 680);
  }

  return (
    <div className="space-y-10">
      <HivePageHeader
        title={agent.name}
        subtitle={
          <span className="font-[family-name:var(--font-inter)] text-sm text-muted-foreground">
            Role <span className="text-data">{agent.role}</span> · swarm{" "}
            <span className="font-mono text-xs text-zinc-400">{agent.swarm_id ?? "—"}</span>
          </span>
        }
        actions={
          <div className="flex flex-wrap items-center gap-3">
            <AgentDetailRunNow agentId={agent.id} />
            <Link
              href={`/agents/${encodeURIComponent(agent.id)}/edit`}
              className="rounded-lg border border-pollen/35 px-3 py-1.5 font-mono text-xs text-pollen hover:bg-pollen/10"
              prefetch={false}
            >
              Edit config
            </Link>
            <Link href="/agents" className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-pollen hover:underline">
              ← roster
            </Link>
          </div>
        }
      />

      <section className="rounded-3xl border border-cyan/[0.12] bg-hive-card/92 p-6 neon-border-pg lg:p-8">
        <div className="flex flex-wrap items-start gap-8">
          <div className="hive-hex flex h-36 w-32 items-center justify-center bg-black/55 text-4xl glow-cyan">🐝</div>
          <div className="min-w-[220px] flex-1 space-y-4">
            <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase tracking-[0.2em] text-zinc-500">
              Pollen ledger
            </p>
            <p className="font-[family-name:var(--font-space-grotesk)] text-4xl text-pollen tabular-nums">
              {agent.pollen_points.toFixed(2)}
            </p>
            <p className="font-[family-name:var(--font-inter)] text-sm text-muted-foreground">
              Status · <span className="text-[#fafafa]">{agent.status}</span>
            </p>
            {beeCfg?.schedule_value ? (
              <div className="flex flex-wrap items-center gap-2 font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-400">
                <span className="text-data">⏰</span>
                <span>{beeCfg.schedule_value}</span>
                <span
                  className={`rounded-full border px-2 py-0.5 text-[10px] ${
                    beeCfg.is_active
                      ? "border-success/40 bg-success/10 text-success"
                      : "border-white/15 text-zinc-500"
                  }`}
                >
                  {beeCfg.is_active ? "active" : "paused"}
                </span>
              </div>
            ) : null}
            <AgentRemoteControls agentId={agent.id} />
          </div>
        </div>
      </section>

      {beeCfg && lastSnippet ? (
        <section className="rounded-3xl border border-cyan/[0.08] bg-black/35 p-6">
          <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.18em] text-zinc-500">
            Last run result
          </p>
          <pre className="mt-3 line-clamp-6 overflow-hidden whitespace-pre-wrap font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-200">
            {lastSnippet}
          </pre>
          {beeCfg.last_run_at ? (
            <p className="mt-3 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500">
              Last run · {new Date(beeCfg.last_run_at).toLocaleString()}
              {typeof beeCfg.run_count === "number" ? ` · ${beeCfg.run_count} queued runs logged` : null}
            </p>
          ) : null}
        </section>
      ) : null}

      <section>
        <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">
          Mission log
        </h2>
        <p className="mt-2 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
          Last backlog rows referencing this bee (agent_id linkage).
        </p>
        <ul className="mt-4 space-y-3">
          {tasks.length === 0 ? (
            <li className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-zinc-500">No routed tasks yet.</li>
          ) : (
            tasks.map((t) => (
              <li
                key={t.id}
                className="rounded-2xl border border-white/[0.06] bg-black/35 px-4 py-3 font-[family-name:var(--font-inter)] text-sm text-[#fafafa]"
              >
                <span className="font-mono text-xs text-zinc-500">{t.id}</span> · {t.title}
                <span className="ml-2 text-xs uppercase text-data">{t.status}</span>
              </li>
            ))
          )}
        </ul>
      </section>
    </div>
  );
}
