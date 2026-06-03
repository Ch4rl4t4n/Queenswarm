"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { AgentSuggestionsConfigurationsPanel } from "@/components/hive/agent-suggestions-configurations-panel";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
import type { AgentInitiativePolicy, AgentSuggestionRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface AgentSuggestionsPanelProps {
  className?: string;
}

export function AgentSuggestionsPanel({ className }: AgentSuggestionsPanelProps) {
  const [rows, setRows] = useState<AgentSuggestionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [policy, setPolicy] = useState<AgentInitiativePolicy>({
    auto_approve_enabled: false,
    include_high_risk: false,
  });
  const autoApproveLock = useRef(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [body, policyBody] = await Promise.all([
        hiveGet<AgentSuggestionRow[]>("agents/suggestions?status_filter=pending&limit=80"),
        hiveGet<AgentInitiativePolicy>("agents/suggestions/policy"),
      ]);
      setRows(Array.isArray(body) ? body : []);
      setPolicy(policyBody);
    } catch (err) {
      setError(err instanceof HiveApiError ? err.message : "Unable to load suggestions");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, DASHBOARD_BOOT_STAGGER_MS.agentSuggestions);
    return () => window.clearTimeout(timer);
  }, [load]);

  useEffect(() => {
    if (!policy.auto_approve_enabled) return;
    const tick = () => {
      if (autoApproveLock.current) return;
      autoApproveLock.current = true;
      void load().finally(() => {
        autoApproveLock.current = false;
      });
    };
    tick();
    const interval = window.setInterval(tick, 90_000);
    return () => window.clearInterval(interval);
  }, [load, policy.auto_approve_enabled]);

  async function review(id: string, decision: "approve" | "reject"): Promise<void> {
    setBusyId(id);
    setError(null);
    try {
      await hivePostJson(`agents/suggestions/${encodeURIComponent(id)}/review`, { decision });
      await load();
    } catch (err) {
      setError(err instanceof HiveApiError ? err.message : "Review failed");
    } finally {
      setBusyId(null);
    }
  }

  async function approveAll(includeHighRisk: boolean): Promise<void> {
    const pending = rows.filter((r) => r.status === "pending");
    if (!pending.length) return;
    setBulkBusy(true);
    try {
      await hivePostJson("agents/suggestions/bulk-review", {
        decision: "approve",
        include_high_risk: includeHighRisk,
        limit: 100,
      });
      await load();
      toast.success("Bulk approve complete.");
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Bulk approve failed");
    } finally {
      setBulkBusy(false);
    }
  }

  async function rejectAll(): Promise<void> {
    setBulkBusy(true);
    try {
      await hivePostJson("agents/suggestions/bulk-review", {
        decision: "reject",
        include_high_risk: true,
        limit: 100,
      });
      await load();
      toast.success("All pending suggestions rejected.");
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Bulk reject failed");
    } finally {
      setBulkBusy(false);
    }
  }

  const pendingCount = rows.filter((row) => row.status === "pending").length;

  return (
    <V4Card id="agent-suggestions" className={cn("v4-card-interactive scroll-mt-28", className)}>
      <V4CardHeader
        title="Agent suggestions"
        description="Reflection · initiative · workflow deltas · auto-approve rules."
        actions={
          <>
            <V4Badge tone="purple">{pendingCount} pending</V4Badge>
            <button type="button" onClick={() => void load()} className="qs-btn qs-btn--ghost qs-btn--sm">
              Refresh
            </button>
          </>
        }
      />

      {loading ? <p className="mb-4 text-sm text-(--qs-text-3)">Loading initiative suggestions…</p> : null}

      {!loading ? (
        <AgentSuggestionsConfigurationsPanel
          rows={rows}
          policy={policy}
          busyId={busyId}
          bulkBusy={bulkBusy}
          policyBusy={false}
          onPolicyChange={setPolicy}
          onReload={load}
          onReview={review}
          onApproveAll={approveAll}
          onRejectAll={rejectAll}
        />
      ) : null}

      {error ? <p className="mt-3 text-sm text-(--qs-red)">{error}</p> : null}
    </V4Card>
  );
}
