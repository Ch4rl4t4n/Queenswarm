"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { useMemo } from "react";

import { V4Card, V4CardHeader } from "@/components/ui/v4";
import type { AgentRow } from "@/lib/hive-types";

const BEE_ROLE_CATALOG: {
  roleKeys: string[];
  emoji: string;
  name: string;
  description: string;
}[] = [
  { roleKeys: ["generic", "worker", ""], emoji: "🐝", name: "GenericBee", description: "Catch-all when role is undecided." },
  { roleKeys: ["scraper"], emoji: "🔍", name: "ScraperBee", description: "Pulls data from foragers and the web." },
  { roleKeys: ["evaluator"], emoji: "🧪", name: "EvaluatorBee", description: "Scores and ranks outputs." },
  { roleKeys: ["simulator"], emoji: "🔮", name: "SimulatorBee", description: "Runs sandboxed cost / behavior sims." },
  { roleKeys: ["reporter"], emoji: "📜", name: "ReporterBee", description: "Narrates outcomes into Ballroom." },
  { roleKeys: ["trader"], emoji: "💹", name: "TraderBee", description: "Executes paper or live trading actions." },
  { roleKeys: ["marketer"], emoji: "📢", name: "MarketerBee", description: "Crafts campaigns and outreach copy." },
  { roleKeys: ["blog_writer"], emoji: "📝", name: "BlogWriterBee", description: "Long-form drafts and article chains." },
  { roleKeys: ["social_poster"], emoji: "📲", name: "SocialPosterBee", description: "Schedules and posts to social channels." },
  { roleKeys: ["learner"], emoji: "🎓", name: "LearnerBee", description: "Adapts from reflections, top-K imitation." },
  { roleKeys: ["recipe_keeper"], emoji: "📚", name: "RecipeKeeperBee", description: "Curates and serves recipe library." },
];

function normalizeRole(role: string): string {
  return role.trim().toLowerCase().replace(/-/g, "_");
}

function agentRoleBucket(role: string): string {
  const r = normalizeRole(role);
  for (const row of BEE_ROLE_CATALOG) {
    if (row.name === "GenericBee") {
      continue;
    }
    if (row.roleKeys.some((k) => normalizeRole(k) === r)) {
      return row.name;
    }
  }
  return "GenericBee";
}

interface BeeRoleTypesSectionProps {
  agents: AgentRow[];
}

/** Bee role archetype catalog — counts from live agent roster. */
export function BeeRoleTypesSection({ agents }: BeeRoleTypesSectionProps) {
  const rows = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of BEE_ROLE_CATALOG) {
      counts.set(row.name, 0);
    }
    for (const agent of agents) {
      const bucket = agentRoleBucket(agent.role);
      counts.set(bucket, (counts.get(bucket) ?? 0) + 1);
    }
    return BEE_ROLE_CATALOG.map((row) => ({
      ...row,
      count: counts.get(row.name) ?? 0,
    }));
  }, [agents]);

  return (
    <V4Card>
      <V4CardHeader
        title="Bee role types"
        description="11 role archetypes. Each bee picks one — clone, extend, or compose for custom workers."
        actions={
          <Link href="/agents/new" className="qs-btn qs-btn--ghost qs-btn--sm gap-2">
            <Plus className="h-4 w-4" aria-hidden />
            New template
          </Link>
        }
      />
      <div className="v4-cols-3">
        {rows.map((row) => (
          <article key={row.name} className="v4-bee-role-card">
            <div className="v4-bee-mark" aria-hidden>
              {row.emoji}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-sm font-semibold text-(--qs-text)">{row.name}</h3>
                <span className="shrink-0 text-[11px] text-(--qs-text-3)">×{row.count}</span>
              </div>
              <p className="mt-1 text-xs leading-snug text-(--qs-text-3)">{row.description}</p>
            </div>
          </article>
        ))}
      </div>
    </V4Card>
  );
}
