"use client";

import { Loader2Icon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import {
  FactoryLlmReadinessBanner,
  factoryBuildDisabled,
  type FactoryLlmReadiness,
} from "@/components/apps-tools/factory-llm-readiness-banner";
import {
  FactoryQueueTaskCard,
  isStuckFactoryBuild,
} from "@/components/apps-tools/factory-queue-task-card";
import { AgentSessionReportDialog } from "@/components/hive/agent-session-report-dialog";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

interface SkillOpportunityRow {
  id: string;
  niche: string;
  title: string;
  rationale: string;
  composite_score: number;
  suggested_price_eur_cents: number;
  status: string;
  supervisor_session_id: string | null;
  supervisor_session_status: string | null;
  supervisor_session_error?: string | null;
  forge_suggestion_id: string | null;
  forge_review_status?: string | null;
  forge_quality_passed?: boolean | null;
  forge_critic_approved?: boolean | null;
  forge_issues?: string[];
  progress_phase?: string;
  progress_label?: string;
  progress_detail?: string | null;
}

interface SkillFactorySnapshot {
  opportunities: SkillOpportunityRow[];
  queue_count: number;
  building_count: number;
  failed_count?: number;
  llm: FactoryLlmReadiness | null;
}

interface MissionFactoryQueuePanelProps {
  /** Fired after queue actions so Mission Home can refresh counts / process rail. */
  onActioned?: () => void;
}

/**
 * Inline Skill Factory build queue — Run / Rebuild / Approve forge without leaving Mission Control.
 */
export function MissionFactoryQueuePanel({ onActioned }: MissionFactoryQueuePanelProps): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<SkillFactorySnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [sessionReportId, setSessionReportId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<SkillFactorySnapshot>("skill-factory/snapshot");
      setSnapshot(data);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Skill Factory queue unavailable.";
      toast.error(msg);
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const queueRows = useMemo(() => {
    const statusRank: Record<string, number> = {
      building: 0,
      awaiting_forge: 1,
      failed: 2,
      queued: 3,
    };
    return (snapshot?.opportunities ?? [])
      .filter((row) => ["queued", "building", "awaiting_forge", "failed"].includes(row.status))
      .sort((a, b) => {
        const rank = (statusRank[a.status] ?? 9) - (statusRank[b.status] ?? 9);
        if (rank !== 0) return rank;
        return (b.composite_score ?? 0) - (a.composite_score ?? 0);
      });
  }, [snapshot?.opportunities]);

  const refreshAfterAction = useCallback(async (): Promise<void> => {
    try {
      const data = await hiveGet<SkillFactorySnapshot>("skill-factory/snapshot");
      setSnapshot(data);
    } catch {
      /* ignore poll errors */
    }
    onActioned?.();
  }, [onActioned]);

  const buildOpportunity = async (id: string): Promise<void> => {
    setBusyId(id);
    try {
      await hivePostJson(`skill-factory/opportunities/${id}/build`, {});
      toast.success("Factory build started.");
      await refreshAfterAction();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Build failed.");
    } finally {
      setBusyId(null);
    }
  };

  const rebuildOpportunity = async (opportunityId: string): Promise<void> => {
    setBusyId(opportunityId);
    try {
      await hivePostJson(`skill-factory/opportunities/${opportunityId}/rebuild`, {});
      toast.success("Rebuild started.");
      await refreshAfterAction();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Rebuild failed.");
    } finally {
      setBusyId(null);
    }
  };

  const dismissOpportunity = async (id: string): Promise<void> => {
    setBusyId(id);
    try {
      await hivePostJson(`skill-factory/opportunities/${id}/dismiss`, {});
      await refreshAfterAction();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Dismiss failed.");
    } finally {
      setBusyId(null);
    }
  };

  const approveForge = async (suggestionId: string, opportunityId: string): Promise<void> => {
    setBusyId(opportunityId);
    try {
      await hivePostJson(`agents/suggestions/${encodeURIComponent(suggestionId)}/review`, {
        decision: "approve",
      });
      toast.success("Skill approved — check Library in harness strip below.");
      await refreshAfterAction();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Approve failed.");
    } finally {
      setBusyId(null);
    }
  };

  const rejectForge = async (opportunityId: string): Promise<void> => {
    setBusyId(opportunityId);
    try {
      await hivePostJson(`skill-factory/opportunities/${opportunityId}/reject-forge`, {});
      toast.success("Forge rejected.");
      await refreshAfterAction();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Reject failed.");
    } finally {
      setBusyId(null);
    }
  };

  const stopQueueSession = async (opportunityId: string, sessionId: string): Promise<void> => {
    setBusyId(opportunityId);
    try {
      await hivePostJson(`agents/sessions/${sessionId}/control`, { action: "stop" });
      toast.success("Build stopped.");
      await refreshAfterAction();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Stop failed.");
    } finally {
      setBusyId(null);
    }
  };

  const runQueueTask = async (opportunityId: string): Promise<void> => {
    const row = (snapshot?.opportunities ?? []).find((item) => item.id === opportunityId);
    if (!row) return;
    if (row.status === "queued") {
      await buildOpportunity(opportunityId);
      return;
    }
    await rebuildOpportunity(opportunityId);
  };

  const factoryLlmShortLabel = useMemo(() => {
    const llm = snapshot?.llm;
    if (!llm?.primary_model) return undefined;
    const match = llm.available_models?.find((row) => row.value === llm.primary_model);
    if (match?.label) {
      const short = match.label.split("(")[0]?.trim();
      return short ? short.slice(0, 28) : match.label.slice(0, 28);
    }
    return llm.primary_model.split("/").pop()?.slice(0, 24);
  }, [snapshot?.llm]);

  if (loading) {
    return (
      <V4Card id="mission-factory-queue" className="scroll-mt-24 md:max-lg:col-span-2" data-testid="mission-factory-queue-panel">
        <p className="flex items-center gap-2 px-4 py-6 text-sm text-(--qs-muted)">
          <Loader2Icon className="size-4 animate-spin" aria-hidden />
          Loading factory queue…
        </p>
      </V4Card>
    );
  }

  if (!snapshot || queueRows.length === 0) {
    return null;
  }

  const buildBlocked = factoryBuildDisabled(snapshot.llm);

  return (
    <>
      <V4Card
        id="mission-factory-queue"
        className="scroll-mt-24 md:max-lg:col-span-2 border-pollen/35 shadow-[0_0_20px_rgba(255,184,0,0.1)]"
        data-testid="mission-factory-queue-panel"
      >
        <V4CardHeader
          kicker="Work"
          title="Factory queue"
          description="Run, rebuild, approve forge — všetko tu, bez skoku do Apps & Tools."
          hint={sectionHintNode("skillFactoryQueue")}
        />
        <div className="space-y-3 px-4 pb-4">
          <FactoryLlmReadinessBanner
            llm={snapshot.llm}
            onSmoked={(next) => setSnapshot((prev) => (prev ? { ...prev, llm: next } : prev))}
          />
          <div className="v4-sessions-list-scroll hive-scrollbar">
            {queueRows.map((row) => (
              <FactoryQueueTaskCard
                key={row.id}
                row={row}
                busyId={busyId}
                buildDisabled={buildBlocked}
                factoryLlmLabel={factoryLlmShortLabel}
                onRun={(id) => void runQueueTask(id)}
                onStop={(id, sessionId) => void stopQueueSession(id, sessionId)}
                onRebuild={(id) => void rebuildOpportunity(id)}
                onDismiss={(id) => void dismissOpportunity(id)}
                onApproveForge={(suggestionId, id) => void approveForge(suggestionId, id)}
                onRejectForge={(id) => void rejectForge(id)}
                onSync={() => void refreshAfterAction()}
                onOpenReport={(sessionId) => setSessionReportId(sessionId)}
              />
            ))}
          </div>
        </div>
      </V4Card>
      <AgentSessionReportDialog
        sessionId={sessionReportId}
        open={sessionReportId !== null}
        onOpenChange={(open) => {
          if (!open) setSessionReportId(null);
        }}
      />
    </>
  );
}
