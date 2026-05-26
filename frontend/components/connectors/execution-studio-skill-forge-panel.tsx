"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { InfoHint } from "@/components/hive/info-hint";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { AgentSuggestionRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

export interface ExecutionStudioSkillForgePanelProps {
  onError: (message: string | null) => void;
}

const SKILL_FORGE_HINT = {
  title: {
    en: "Verified Skill Forge",
    sk: "Verified Skill Forge",
  },
  description: {
    en: "Critic-approved HiveMind sessions become reusable skill drafts. Review and approve to add to the Recipe Library.",
    sk: "HiveMind session schválené criticom → návrh skillu. Schválením pridáš overený workflow do Recipe Library.",
  },
  options: {
    en: [
      "Run Sentinel / HiveMind verify lane until critic approves ingest.",
      "Pending proposals appear here and in Dashboard → Agent suggestions.",
      "Approve → skill markdown saved; reject if draft is off-topic.",
      "Pair with Brain Pack INSTRUCTIONS for publish-lane guardrails.",
    ],
    sk: [
      "Spusti Sentinel / HiveMind verify lane až kým critic schváli ingest.",
      "Pending návrhy sú tu aj v Dashboard → Agent suggestions.",
      "Approve → uloží skill markdown; reject ak draft nesedí.",
      "Skombinuj s Brain Pack INSTRUCTIONS pre publish guardrails.",
    ],
  },
};

function ExecutionStudioSkillForgePanelInner({ onError }: ExecutionStudioSkillForgePanelProps) {
  const [rows, setRows] = useState<AgentSuggestionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      const body = await hiveGet<AgentSuggestionRow[]>("agents/suggestions?status_filter=pending&limit=40");
      setRows(Array.isArray(body) ? body : []);
    } catch (err) {
      onError(err instanceof HiveApiError ? err.message : "Skill forge unavailable");
    } finally {
      setLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    void load();
  }, [load]);

  const forgeRows = useMemo(
    () => rows.filter((row) => row.proposal_type === "verified_skill_forge" && row.status === "pending"),
    [rows],
  );

  async function review(id: string, decision: "approve" | "reject"): Promise<void> {
    setBusyId(id);
    onError(null);
    try {
      const updated = await hivePostJson<AgentSuggestionRow>(
        `agents/suggestions/${encodeURIComponent(id)}/review`,
        { decision },
      );
      setRows((prev) => prev.map((row) => (row.id === id ? updated : row)));
      toast.success(decision === "approve" ? "Skill approved" : "Skill rejected");
    } catch (err) {
      onError(err instanceof HiveApiError ? err.message : "Review failed");
    } finally {
      setBusyId(null);
    }
  }

  if (loading) {
    return (
      <V4Card className="p-4">
        <Loader2 className="h-5 w-5 animate-spin text-(--qs-cyan)" aria-hidden />
      </V4Card>
    );
  }

  if (!forgeRows.length) {
    return null;
  }

  return (
    <V4Card id="skill-forge">
      <V4CardHeader
        kicker="HiveMind"
        title="Verified Skill Forge"
        description={`${forgeRows.length} pending critic-approved skill draft${forgeRows.length === 1 ? "" : "s"}`}
        actions={<InfoHint title={SKILL_FORGE_HINT.title} description={SKILL_FORGE_HINT.description} options={SKILL_FORGE_HINT.options} />}
      />
      <ul className="space-y-3">
        {forgeRows.map((row) => (
          <li
            key={row.id}
            className="v4-dream-cycle-card flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-(--qs-text)">{row.title}</p>
              <p className="mt-0.5 line-clamp-2 text-xs text-(--qs-text-3)">{row.description}</p>
              <div className="mt-1 flex flex-wrap gap-1">
                <V4Badge tone="gold">verified_skill_forge</V4Badge>
                <V4Badge tone="info">{row.proposed_by_role}</V4Badge>
              </div>
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
              <button
                type="button"
                className={cn("qs-btn qs-btn--primary qs-btn--sm", busyId === row.id && "opacity-60")}
                disabled={busyId !== null}
                onClick={() => void review(row.id, "approve")}
              >
                Approve
              </button>
              <button
                type="button"
                className={cn("qs-btn qs-btn--ghost qs-btn--sm", busyId === row.id && "opacity-60")}
                disabled={busyId !== null}
                onClick={() => void review(row.id, "reject")}
              >
                Reject
              </button>
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-(--qs-muted)">
        All agent suggestions:{" "}
        <Link href="/dashboard#agent-suggestions" className="text-(--qs-cyan) underline-offset-2 hover:underline">
          Dashboard deck
        </Link>
      </p>
    </V4Card>
  );
}

export const ExecutionStudioSkillForgePanel = memo(ExecutionStudioSkillForgePanelInner);
