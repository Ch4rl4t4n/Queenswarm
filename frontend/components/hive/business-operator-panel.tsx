"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Activity, Briefcase, ExternalLink, Loader2, Play, Target, Users } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { BusinessApprovalInbox } from "@/components/hive/business-approval-inbox";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader, type V4BadgeTone } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

interface BusinessAction {
  id: string;
  lane: string;
  title: string;
  detail: string;
  priority: "high" | "medium" | "low";
  href: string | null;
}

interface BusinessGoalProgress {
  id: string;
  kind: string;
  label: string;
  target_value: number;
  current_value: number;
  unit: string;
  drift_severity: "ok" | "warning" | "critical";
  drift_detail: string;
}

interface BackgroundBee {
  bee_id: string;
  label: string;
  status: "idle" | "ok" | "attention" | "disabled";
  summary: string;
  pending_count: number;
  last_run_at: string | null;
  href: string | null;
}

interface ProactivePulseChange {
  id: string;
  category: string;
  label: string;
  detail: string;
  severity: "info" | "warn" | "success";
}

interface ProactivePulse {
  enabled: boolean;
  headline: string;
  changes: ProactivePulseChange[];
  autonomous_runs: { id: string; label: string; detail: string }[];
}

interface BusinessOperatorSnapshot {
  enabled: boolean;
  generated_at: string;
  headline?: string;
  tagline: string;
  catalog: {
    product_count: number;
    featured_count: number;
    gumroad_linked_count: number;
    marketing_origin: string;
  };
  revenue: {
    ready_summary?: string;
    scorecard_ready_count?: number | null;
    first_upload_candidate?: string | null;
    next_operator_action?: string;
    missing_reports?: string[];
  };
  missions: {
    triage_count: number;
    ready_count: number;
    in_progress_count: number;
    blocked_count: number;
  };
  top_actions: BusinessAction[];
  goal_stack?: {
    goals: BusinessGoalProgress[];
    drift_count: number;
    critical_drift_count: number;
  } | null;
  background_team?: {
    enabled: boolean;
    bees: BackgroundBee[];
    attention_count: number;
  } | null;
  cross_lane_learning?: {
    enabled: boolean;
    suggestions: Array<{
      id: string;
      recipe_name: string;
      source_domain: string;
      target_domain: string;
      target_lane: string;
      similarity: number;
      rationale: string;
      href: string | null;
    }>;
  } | null;
  harness_profiles?: {
    active_profile_id: string;
    profiles: Array<{ profile_id: string; label: string; description: string }>;
  } | null;
  links: Record<string, string>;
}

interface BusinessDispatchResponse {
  ok: boolean;
  kind: "supervisor_session" | "mission_kanban";
  message: string;
  href: string;
  supervisor_session_id?: string | null;
  task_id?: string | null;
  child_count?: number;
  dispatched_triage_count?: number;
}

function priorityTone(priority: BusinessAction["priority"]): V4BadgeTone {
  if (priority === "high") {
    return "gold";
  }
  if (priority === "medium") {
    return "info";
  }
  return "warn";
}

function BusinessOperatorPanelInner(): JSX.Element | null {
  const router = useRouter();
  const [snapshot, setSnapshot] = useState<BusinessOperatorSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dispatchingId, setDispatchingId] = useState<string | null>(null);
  const [pulse, setPulse] = useState<ProactivePulse | null>(null);
  const [profileBusy, setProfileBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [data, pulseData] = await Promise.all([
        hiveGet<BusinessOperatorSnapshot>("operator/business/snapshot"),
        hiveGet<ProactivePulse>("operator/business/pulse?phase=midday").catch(() => null),
      ]);
      setSnapshot(data);
      setPulse(pulseData?.enabled ? pulseData : null);
      setError(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Business operator unavailable";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleProfileChange = useCallback(
    async (profileId: string) => {
      setProfileBusy(true);
      try {
        await hivePatchJson("operator/business/harness-profiles", {
          active_profile_id: profileId,
        });
        toast.success(`Harness profile: ${profileId}`);
        await load();
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Profile update failed");
      } finally {
        setProfileBusy(false);
      }
    },
    [load],
  );

  const handleDispatch = useCallback(
    async (action: BusinessAction) => {
      setDispatchingId(action.id);
      try {
        const result = await hivePostJson<BusinessDispatchResponse>("operator/business/dispatch", {
          action_id: action.id,
          lane: action.lane,
          title: action.title,
          detail: action.detail,
        });
        toast.success(result.message);
        if (result.kind === "supervisor_session") {
          router.push(result.href);
        } else {
          router.push("/tasks");
        }
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Dispatch failed");
      } finally {
        setDispatchingId(null);
      }
    },
    [router],
  );

  if (loading && !snapshot) {
    return (
      <V4Card className="mb-4 border-pollen/30">
        <div className="flex items-center gap-2 p-4 text-sm text-(--qs-muted)">
          <Loader2 className="size-4 animate-spin text-pollen" aria-hidden />
          Loading business brief…
        </div>
      </V4Card>
    );
  }

  if (error && !snapshot) {
    return (
      <V4Card className="mb-4 border-error/30">
        <p className="p-4 text-sm text-error">{error}</p>
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  const marketingHref = snapshot.links.marketing_skills ?? "https://letagentscook.org/skills";
  const isExternal = (href: string): boolean => href.startsWith("http");

  return (
    <V4Card className="border-pollen/35 bg-pollen/5" id="business-operator">
      <V4CardHeader
        kicker="Chief Business Operator"
        title={snapshot.headline?.trim() || "What to do for the business"}
        description={snapshot.tagline}
        actions={<HiveRefreshButton busy={loading} onClick={() => void load()} />}
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-(--qs-border) bg-(--qs-surface-2) p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-muted)">Catalog live</p>
          <p className="mt-1 font-[family-name:var(--font-hive-mono)] text-2xl font-bold text-pollen">
            {snapshot.catalog.product_count}
          </p>
          <p className="mt-1 text-xs text-(--qs-text-2)">
            {snapshot.catalog.gumroad_linked_count} with Gumroad URL
          </p>
        </div>
        <div className="rounded-lg border border-(--qs-border) bg-(--qs-surface-2) p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-muted)">Scorecard ready</p>
          <p className="mt-1 font-[family-name:var(--font-hive-mono)] text-2xl font-bold text-cyan">
            {snapshot.revenue.scorecard_ready_count ?? "—"}
          </p>
          <p className="mt-1 text-xs text-(--qs-text-2)">{snapshot.revenue.ready_summary ?? "—"}</p>
        </div>
        <div className="rounded-lg border border-(--qs-border) bg-(--qs-surface-2) p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-muted)">Mission queue</p>
          <p className="mt-1 font-[family-name:var(--font-hive-mono)] text-2xl font-bold text-(--qs-text)">
            {snapshot.missions.triage_count}
          </p>
          <p className="mt-1 text-xs text-(--qs-text-2)">triage · {snapshot.missions.in_progress_count} in progress</p>
        </div>
      </div>

      <BusinessApprovalInbox />

      {snapshot.harness_profiles?.profiles?.length ? (
        <div className="mb-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-cyan">Harness profile (AOS1)</p>
          <div className="flex flex-wrap gap-2">
            {snapshot.harness_profiles.profiles.map((profile) => (
              <button
                key={profile.profile_id}
                type="button"
                className={
                  snapshot.harness_profiles?.active_profile_id === profile.profile_id
                    ? "qs-btn qs-btn--primary qs-btn--sm"
                    : "qs-btn qs-btn--ghost qs-btn--sm"
                }
                disabled={profileBusy || loading}
                onClick={() => void handleProfileChange(profile.profile_id)}
              >
                {profile.label}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {snapshot.cross_lane_learning?.enabled && snapshot.cross_lane_learning.suggestions.length > 0 ? (
        <div className="mb-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-pollen">Cross-lane learning (BA7)</p>
          <ul className="space-y-2 text-sm">
            {snapshot.cross_lane_learning.suggestions.slice(0, 3).map((row) => (
              <li key={row.id} className="rounded-lg border border-(--qs-border) bg-(--qs-surface) p-3">
                <p className="font-medium text-(--qs-text)">{row.recipe_name}</p>
                <p className="text-xs text-(--qs-text-2)">
                  {row.source_domain} → {row.target_domain} ({Math.round(row.similarity * 100)}%)
                </p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {snapshot.goal_stack && snapshot.goal_stack.goals.length > 0 ? (
        <div className="mb-4">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-pollen">
            <Target className="size-3.5" aria-hidden />
            Goal stack
            {snapshot.goal_stack.critical_drift_count > 0 ? (
              <V4Badge tone="gold">{snapshot.goal_stack.critical_drift_count} drift</V4Badge>
            ) : null}
          </p>
          <ul className="space-y-2">
            {snapshot.goal_stack.goals.map((goal) => (
              <li
                key={goal.id}
                className="rounded-lg border border-(--qs-border) bg-(--qs-surface) p-3 text-sm"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-(--qs-text)">{goal.label}</span>
                  <V4Badge tone={goal.drift_severity === "critical" ? "gold" : goal.drift_severity === "warning" ? "warn" : "ok"}>
                    {goal.drift_severity}
                  </V4Badge>
                </div>
                <p className="mt-1 text-xs text-(--qs-text-2)">
                  {goal.drift_detail || `${goal.current_value}/${goal.target_value} ${goal.unit}`}
                </p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {snapshot.background_team?.enabled && snapshot.background_team.bees.length > 0 ? (
        <div className="mb-4">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-cyan">
            <Users className="size-3.5" aria-hidden />
            Background team
            {snapshot.background_team.attention_count > 0 ? (
              <V4Badge tone="warn">{snapshot.background_team.attention_count} attention</V4Badge>
            ) : null}
          </p>
          <div className="grid gap-2 sm:grid-cols-3">
            {snapshot.background_team.bees.map((bee) => (
              <div
                key={bee.bee_id}
                className="rounded-lg border border-(--qs-border) bg-(--qs-surface-2) p-3 text-xs"
              >
                <p className="font-semibold text-(--qs-text)">{bee.label}</p>
                <p className="mt-1 text-(--qs-muted)">{bee.status}</p>
                <p className="mt-1 text-(--qs-text-2)">{bee.summary || "—"}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {pulse ? (
        <div className="mb-4 rounded-lg border border-cyan/30 bg-cyan/5 p-3">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-cyan">
            <Activity className="size-3.5" aria-hidden />
            Midday pulse
          </p>
          <p className="text-sm font-medium text-(--qs-text)">{pulse.headline}</p>
          {pulse.changes.length > 0 ? (
            <ul className="mt-2 space-y-1 text-xs text-(--qs-text-2)">
              {pulse.changes.slice(0, 4).map((change) => (
                <li key={change.id}>• {change.label}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <div className="mb-4">
        <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-pollen">
          <Target className="size-3.5" aria-hidden />
          Top 3 actions
        </p>
        <ul className="space-y-2">
          {snapshot.top_actions.map((action) => {
            const tone = priorityTone(action.priority);
            const dispatchBusy = dispatchingId === action.id;
            const content = (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <V4Badge tone={tone}>{action.priority}</V4Badge>
                  <span className="text-[10px] uppercase tracking-wider text-(--qs-muted)">{action.lane}</span>
                </div>
                <p className="mt-1 font-medium text-(--qs-text)">{action.title}</p>
                <p className="mt-0.5 text-xs text-(--qs-text-2)">{action.detail}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="qs-btn qs-btn--primary qs-btn--sm gap-1"
                    disabled={dispatchBusy || loading}
                    onClick={() => void handleDispatch(action)}
                  >
                    {dispatchBusy ? (
                      <Loader2 className="size-3.5 animate-spin" aria-hidden />
                    ) : (
                      <Play className="size-3.5" aria-hidden />
                    )}
                    Dispatch
                  </button>
                </div>
              </>
            );
            const className = cn(
              "block rounded-lg border border-(--qs-border) bg-(--qs-surface) p-3 transition-colors",
              action.href && "hover:border-pollen/40",
            );
            if (!action.href) {
              return (
                <li key={action.id} className={className}>
                  {content}
                </li>
              );
            }
            if (isExternal(action.href)) {
              return (
                <li key={action.id}>
                  <a href={action.href} className={className} target="_blank" rel="noopener noreferrer">
                    {content}
                  </a>
                </li>
              );
            }
            return (
              <li key={action.id}>
                <Link href={action.href} className={className}>
                  {content}
                </Link>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="flex flex-wrap gap-2">
        <Link href="/agents#sessions" className="qs-btn qs-btn--primary qs-btn--sm gap-1">
          <Briefcase className="size-4" aria-hidden />
          Agents → Sessions
        </Link>
        <Link href="/tasks" className="qs-btn qs-btn--ghost qs-btn--sm gap-1">
          <Briefcase className="size-4" aria-hidden />
          Mission Control
        </Link>
        <a
          href={marketingHref}
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
          target="_blank"
          rel="noopener noreferrer"
        >
          <ExternalLink className="size-4" aria-hidden />
          letagentscook.org/skills
        </a>
        <Link href="/factory" className="qs-btn qs-btn--ghost qs-btn--sm">
          Factory queue
        </Link>
      </div>
    </V4Card>
  );
}

export const BusinessOperatorPanel = memo(BusinessOperatorPanelInner);
BusinessOperatorPanel.displayName = "BusinessOperatorPanel";
