"use client";

import Link from "next/link";
import { PencilIcon, Plus, XIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveDelete, hiveGet } from "@/lib/api";
import type { AgentRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

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

interface AgentTemplateRow {
  id: string;
  name: string;
  description: string;
  icon: string;
}

interface TeamOverviewResponse {
  tenant_role: string;
}

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
  const [templates, setTemplates] = useState<AgentTemplateRow[]>([]);
  const [tenantRole, setTenantRole] = useState("guest");
  const [deleteTarget, setDeleteTarget] = useState<AgentTemplateRow | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  const canManageTemplates = tenantRole === "owner" || tenantRole === "admin";

  const refreshTemplates = useCallback(async () => {
    try {
      const rows = await hiveGet<AgentTemplateRow[]>("agent-templates");
      setTemplates(rows);
    } catch {
      setTemplates([]);
    }
  }, []);

  useEffect(() => {
    void refreshTemplates();
    void hiveGet<TeamOverviewResponse>("settings/team")
      .then((overview) => setTenantRole(String(overview.tenant_role || "guest")))
      .catch(() => setTenantRole("guest"));
  }, [refreshTemplates]);

  const templateByName = useMemo(() => new Map(templates.map((row) => [row.name, row])), [templates]);

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
      template: templateByName.get(row.name) ?? null,
    }));
  }, [agents, templateByName]);

  async function confirmDeleteTemplate() {
    if (!deleteTarget || !canManageTemplates) {
      return;
    }
    setDeleteBusy(true);
    try {
      await hiveDelete<void>(`agent-templates/${encodeURIComponent(deleteTarget.id)}`);
      setDeleteTarget(null);
      await refreshTemplates();
    } catch (error) {
      window.alert(
        `Template delete failed: ${error instanceof HiveApiError ? error.message : error instanceof Error ? error.message : String(error)}`,
      );
    } finally {
      setDeleteBusy(false);
    }
  }

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
          <article
            key={row.name}
            className={cn("relative v4-bee-role-card", canManageTemplates && row.template && "pt-10")}
          >
            {canManageTemplates && row.template ? (
              <div className="absolute right-2 top-2 z-10 flex items-center gap-1.5">
                <Link
                  href={`/agents/new?editTemplate=${encodeURIComponent(row.template.id)}`}
                  aria-label={`Edit template ${row.name}`}
                  className="flex h-9 w-9 items-center justify-center rounded-lg border border-(--qs-border) bg-black/45 text-(--qs-text-2) transition hover:border-(--qs-border-2) hover:text-pollen touch-manipulation"
                >
                  <PencilIcon className="h-4 w-4" aria-hidden strokeWidth={2.25} />
                </Link>
                <button
                  type="button"
                  aria-label={`Delete template ${row.name}`}
                  disabled={deleteBusy}
                  className="flex h-9 w-9 items-center justify-center rounded-lg border border-danger/45 bg-danger/12 text-danger transition hover:border-danger hover:bg-danger/20 disabled:opacity-40 touch-manipulation"
                  onClick={() => setDeleteTarget(row.template)}
                >
                  <XIcon className="h-4 w-4" aria-hidden strokeWidth={2.5} />
                </button>
              </div>
            ) : null}
            <div className="v4-bee-mark" aria-hidden>
              {row.template?.icon || row.emoji}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-sm font-semibold text-(--qs-text)">{row.name}</h3>
                <span className="shrink-0 text-[11px] text-(--qs-text-3)">×{row.count}</span>
              </div>
              <p className="mt-1 text-xs leading-snug text-(--qs-text-3)">
                {row.template?.description || row.description}
              </p>
            </div>
          </article>
        ))}
      </div>

      <ConfirmModal
        open={deleteTarget !== null}
        title="Delete template?"
        message={
          deleteTarget ? `Remove “${deleteTarget.name}” from the tenant library. This cannot be undone.` : ""
        }
        confirmLabel="Delete"
        danger
        onConfirm={() => void confirmDeleteTemplate()}
        onCancel={() => setDeleteTarget(null)}
      />
    </V4Card>
  );
}
