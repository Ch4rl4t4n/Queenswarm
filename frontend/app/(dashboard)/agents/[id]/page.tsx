import Link from "next/link";
import { notFound } from "next/navigation";

import { AgentRemoteControls } from "@/components/hive/agent-remote-controls";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow, TaskRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

interface AgentDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function AgentDetailPage(props: AgentDetailPageProps) {
  const { id } = await props.params;
  const agent = await hiveServerRawJson<AgentRow>(`/agents/${encodeURIComponent(id)}`);
  const recentTasks = await hiveServerRawJson<TaskRow[]>(
    `/tasks?agent_id=${encodeURIComponent(id)}&limit=50`,
  );

  if (!agent) {
    notFound();
  }

  const tasks = recentTasks ?? [];

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
            <AgentRemoteControls agentId={agent.id} />
          </div>
        </div>
      </section>

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
