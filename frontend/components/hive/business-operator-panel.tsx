"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Briefcase, ExternalLink, Loader2, Play } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { BusinessApprovalInbox } from "@/components/hive/business-approval-inbox";
import { InlineSectionHintKey } from "@/components/hive/inline-section-hint";
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
  catalog_wave?: {
    current_wave: string;
    target_next: number;
    mk6_target: number;
    scorecard_clean_count: number;
    catalog_deduped_count: number;
    gap_to_next_wave: number;
    gap_to_mk6: number;
    seed_pending_count: number;
    next_operator_action: string;
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
  simulation_pass_rate?: {
    enabled: boolean;
    status: "healthy" | "warn" | "critical" | "unknown";
    trend: "up" | "down" | "stable";
    pass_rate_7d_pct: number | null;
    pass_rate_30d_pct: number | null;
    total_7d: number;
    passed_7d: number;
    failed_7d: number;
    inconclusive_7d: number;
    gate_threshold_pct: number;
    operator_hint: string;
    daily: Array<{ date: string; total: number; passed: number; pass_rate_pct: number }>;
  } | null;
  analytics_routine?: {
    enabled: boolean;
    routine_status: string;
    routine_name: string;
    report_title: string | null;
    critic_score_label: string | null;
    critic_passed: boolean;
    export_ready: boolean;
    connector_ready_count: number;
    morning_brief_line: string;
    operator_hint: string;
    workspace_href: string;
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

function sparkBarClass(passRatePct: number, total: number): string {
  if (total <= 0) {
    return "h-1";
  }
  if (passRatePct >= 90) {
    return "h-12";
  }
  if (passRatePct >= 70) {
    return "h-9";
  }
  if (passRatePct >= 50) {
    return "h-6";
  }
  if (passRatePct >= 25) {
    return "h-4";
  }
  return "h-2";
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
      <V4Card className="border-pollen/30">
        <div className="flex items-center gap-2 p-4 text-sm text-(--qs-muted)">
          <Loader2 className="size-4 animate-spin text-pollen" aria-hidden />
          Loading business brief…
        </div>
      </V4Card>
    );
  }

  if (error && !snapshot) {
    return (
      <V4Card className="border-error/30">
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
    <div className="space-y-4" id="business-operator">
      <V4Card className="border-pollen/35 bg-pollen/5">
        <V4CardHeader
          kicker="Chief Business Operator"
          title={snapshot.headline?.trim() || "What to do for the business"}
          description={snapshot.tagline}
          hint={<InlineSectionHintKey hintKey="businessOperator" />}
          actions={<HiveRefreshButton busy={loading} onClick={() => void load()} />}
        />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
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
            <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-muted)">MK6 wave</p>
            <p className="mt-1 font-[family-name:var(--font-hive-mono)] text-2xl font-bold text-success">
              {snapshot.catalog_wave?.scorecard_clean_count ?? snapshot.revenue.scorecard_ready_count ?? "—"}
              <span className="text-base text-(--qs-text-3)">
                /{snapshot.catalog_wave?.mk6_target ?? 50}
              </span>
            </p>
            <p className="mt-1 text-xs text-(--qs-text-2)">
              {snapshot.catalog_wave?.current_wave?.replace("_", " ") ?? "wave"} · gap{" "}
              {snapshot.catalog_wave?.gap_to_mk6 ?? "—"}
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
            <p className="mt-1 text-xs text-(--qs-text-2)">
              triage · {snapshot.missions.in_progress_count} in progress
            </p>
          </div>
        </div>
        {snapshot.catalog_wave?.next_operator_action ? (
          <p className="mt-3 text-xs text-(--qs-text-2)">
            <span className="font-semibold text-pollen">MK6:</span> {snapshot.catalog_wave.next_operator_action}
          </p>
        ) : null}
      </V4Card>

      {snapshot.simulation_pass_rate?.enabled ? (
        <V4Card
          className={cn(
            "border-(--qs-border)",
            snapshot.simulation_pass_rate.status === "critical"
              ? "border-(--qs-red)/40 bg-(--qs-red)/5"
              : snapshot.simulation_pass_rate.status === "warn"
                ? "border-pollen/35 bg-pollen/5"
                : "border-success/30 bg-success/5",
          )}
          data-testid="simulation-pass-rate-panel"
        >
          <V4CardHeader
            kicker="TR2"
            title="Simulation pass rate"
            description="Verify-first harness KPI — swarm audits scoped to your tenant tasks."
          />
          <div className="flex flex-wrap items-center gap-2">
            <V4Badge
              tone={
                snapshot.simulation_pass_rate.status === "healthy"
                  ? "ok"
                  : snapshot.simulation_pass_rate.status === "warn"
                    ? "warn"
                    : snapshot.simulation_pass_rate.status === "critical"
                      ? "err"
                      : "info"
              }
            >
              {snapshot.simulation_pass_rate.status}
            </V4Badge>
            <V4Badge tone="info">trend {snapshot.simulation_pass_rate.trend}</V4Badge>
            <span className="font-mono text-xs text-(--qs-text-3)">
              gate {snapshot.simulation_pass_rate.gate_threshold_pct}%
            </span>
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2">
              <p className="text-[10px] uppercase tracking-wide text-(--qs-text-4)">7-day pass rate</p>
              <p className="mt-1 font-mono text-xl font-bold text-success">
                {snapshot.simulation_pass_rate.pass_rate_7d_pct ?? "—"}%
              </p>
              <p className="text-[11px] text-(--qs-text-3)">
                {snapshot.simulation_pass_rate.passed_7d}/{snapshot.simulation_pass_rate.total_7d} passed
              </p>
            </div>
            <div className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2">
              <p className="text-[10px] uppercase tracking-wide text-(--qs-text-4)">30-day pass rate</p>
              <p className="mt-1 font-mono text-xl font-bold text-cyan">
                {snapshot.simulation_pass_rate.pass_rate_30d_pct ?? "—"}%
              </p>
            </div>
            <div className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2">
              <p className="text-[10px] uppercase tracking-wide text-(--qs-text-4)">Outcomes (7d)</p>
              <p className="mt-1 font-mono text-sm text-(--qs-text-2)">
                fail {snapshot.simulation_pass_rate.failed_7d} · inconclusive{" "}
                {snapshot.simulation_pass_rate.inconclusive_7d}
              </p>
            </div>
          </div>
          <div className="mt-3 flex h-16 items-end gap-1" aria-label="7-day simulation pass rate sparkline">
            {snapshot.simulation_pass_rate.daily.map((day) => (
              <div key={day.date} className="flex flex-1 flex-col items-center gap-1">
                <div
                  className={cn("w-full rounded-sm bg-cyan/30", sparkBarClass(day.pass_rate_pct, day.total))}
                  title={`${day.date}: ${day.pass_rate_pct}% (${day.passed}/${day.total})`}
                />
                <span className="font-mono text-[9px] text-(--qs-text-4)">{day.date.slice(5)}</span>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-(--qs-text-3)">{snapshot.simulation_pass_rate.operator_hint}</p>
        </V4Card>
      ) : null}

      {snapshot.analytics_routine?.enabled ? (
        <V4Card data-testid="cbo-analytics-routine">
          <V4CardHeader
            kicker="DA9"
            title="Analytics deck routine"
            description={snapshot.analytics_routine.operator_hint}
            actions={
              <V4Badge tone={snapshot.analytics_routine.export_ready ? "ok" : "info"}>
                {snapshot.analytics_routine.routine_status}
              </V4Badge>
            }
          />
          <p className="px-4 text-sm text-(--qs-text-2)">{snapshot.analytics_routine.morning_brief_line}</p>
          <div className="flex flex-wrap gap-2 px-4 pb-4">
            <V4Badge tone="info">{snapshot.analytics_routine.connector_ready_count} connectors</V4Badge>
            {snapshot.analytics_routine.critic_score_label ? (
              <V4Badge tone={snapshot.analytics_routine.critic_passed ? "ok" : "warn"}>
                critic {snapshot.analytics_routine.critic_score_label}
              </V4Badge>
            ) : null}
            <Link href={snapshot.analytics_routine.workspace_href} className="qs-btn qs-btn--ghost qs-btn--sm">
              Analytics workspace
            </Link>
          </div>
        </V4Card>
      ) : null}

      <V4Card>
        <BusinessApprovalInbox />
      </V4Card>

      {snapshot.harness_profiles?.profiles?.length ? (
        <V4Card>
          <V4CardHeader
            kicker="AOS1"
            title="Harness profile"
            description="Switch marketing, factory, trading, or general operator presets."
          />
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
        </V4Card>
      ) : null}

      {snapshot.cross_lane_learning?.enabled && snapshot.cross_lane_learning.suggestions.length > 0 ? (
        <V4Card>
          <V4CardHeader
            kicker="BA7"
            title="Cross-lane learning"
            description="Recipes worth copying across marketing, factory, and trading lanes."
          />
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
        </V4Card>
      ) : null}

      {snapshot.goal_stack && snapshot.goal_stack.goals.length > 0 ? (
        <V4Card>
          <V4CardHeader
            kicker="Goals"
            title="Goal stack"
            description="Business goal drift — simulate-first before live operator actions."
            actions={
              snapshot.goal_stack.critical_drift_count > 0 ? (
                <V4Badge tone="gold">{snapshot.goal_stack.critical_drift_count} drift</V4Badge>
              ) : undefined
            }
          />
          <ul className="space-y-2">
            {snapshot.goal_stack.goals.map((goal) => (
              <li
                key={goal.id}
                className="rounded-lg border border-(--qs-border) bg-(--qs-surface) p-3 text-sm"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-(--qs-text)">{goal.label}</span>
                  <V4Badge
                    tone={
                      goal.drift_severity === "critical"
                        ? "gold"
                        : goal.drift_severity === "warning"
                          ? "warn"
                          : "ok"
                    }
                  >
                    {goal.drift_severity}
                  </V4Badge>
                </div>
                <p className="mt-1 text-xs text-(--qs-text-2)">
                  {goal.drift_detail || `${goal.current_value}/${goal.target_value} ${goal.unit}`}
                </p>
              </li>
            ))}
          </ul>
        </V4Card>
      ) : null}

      {snapshot.background_team?.enabled && snapshot.background_team.bees.length > 0 ? (
        <V4Card>
          <V4CardHeader
            kicker="Team"
            title="Background team"
            description="Autonomous bees running on cron — attention flags only when needed."
            actions={
              snapshot.background_team.attention_count > 0 ? (
                <V4Badge tone="warn">{snapshot.background_team.attention_count} attention</V4Badge>
              ) : undefined
            }
          />
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
        </V4Card>
      ) : null}

      {pulse ? (
        <V4Card>
          <V4CardHeader
            kicker="Pulse"
            title="Midday pulse"
            description="Autonomous run summary and notable changes since morning brief."
          />
          <p className="text-sm font-medium text-(--qs-text)">{pulse.headline}</p>
          {pulse.changes.length > 0 ? (
            <ul className="mt-2 space-y-1 text-xs text-(--qs-text-2)">
              {pulse.changes.slice(0, 4).map((change) => (
                <li key={change.id}>• {change.label}</li>
              ))}
            </ul>
          ) : null}
        </V4Card>
      ) : null}

      <V4Card>
        <V4CardHeader
          kicker="Dispatch"
          title="Top 3 actions"
          description="Highest-impact business moves — dispatch to session or Mission Kanban."
        />
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
        <div className="mt-4 flex flex-wrap gap-2 border-t border-(--qs-border) pt-4">
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
    </div>
  );
}

export const BusinessOperatorPanel = memo(BusinessOperatorPanelInner);
BusinessOperatorPanel.displayName = "BusinessOperatorPanel";
