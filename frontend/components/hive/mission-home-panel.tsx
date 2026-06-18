"use client";

import Link from "next/link";
import { ArrowRight, CalendarClock, CheckCircle2, Loader2, Shield, Sparkles, Zap, Brain } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";

import { HivePanelSectionSkeleton } from "@/components/hive/hive-panel-section-skeleton";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { ProcessRail, type ProcessStep, type ProcessStepId } from "@/components/hive/process-rail";
import { CatalogWaveWidget } from "@/components/hive/catalog-wave-widget";
import { FactoryLaunchWidget } from "@/components/hive/factory-launch-widget";
import { RevenueFunnelStrip } from "@/components/hive/revenue-funnel-strip";
import { RapidLoopWidget } from "@/components/hive/rapid-loop-widget";
import { SubSwarmFleetWidget } from "@/components/hive/sub-swarm-fleet-widget";
import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import { cn } from "@/lib/utils";

interface MissionBriefBullet {
  text: string;
  source: string;
}

interface MissionAction {
  id: string;
  title: string;
  detail: string;
  href: string | null;
  priority: number;
}

interface MissionApproval {
  id: string;
  title: string;
  detail: string;
  href: string;
  kind: string;
}

interface MissionActiveSession {
  session_id: string;
  goal: string;
  status: string;
  progress_label: string;
  progress_pct: number;
  loop_chip: string;
  href: string;
}

interface MissionMemoryLayer {
  id: "soul" | "memory" | "user";
  label: string;
  preview: string;
  char_count: number;
  filled: boolean;
  href: string;
}

interface MissionMemoryStrip {
  layers: MissionMemoryLayer[];
  total_chars: number;
  max_chars: number;
  usage_pct: number;
}

interface MissionStudioEntry {
  id: string;
  title: string;
  detail: string;
  href: string;
}

interface MissionCalendarEvent {
  id: string;
  title: string;
  start_at: string | null;
  end_at: string | null;
  detail: string;
  href: string;
}

interface MissionLifeOsStrip {
  enabled: boolean;
  connected: boolean;
  event_count: number;
  message: string;
  events: MissionCalendarEvent[];
  connect_href: string;
}

type AutopilotLaneStatus = "active" | "bound" | "missing" | "paused";

interface MissionAutopilotLane {
  id: string;
  label: string;
  group: "trio" | "four_lane";
  status: AutopilotLaneStatus;
  detail: string;
  schedule_cron: string | null;
}

interface MissionAutopilotStrip {
  enabled: boolean;
  routines_enabled: boolean;
  trio_bound: number;
  trio_total: number;
  four_lanes_active: number;
  four_lanes_total: number;
  digest_pending: number;
  cron_lane_count: number;
  message: string;
  lanes: MissionAutopilotLane[];
  harness_href: string;
  four_lanes_href: string;
  digest_href: string;
}

interface MissionJarvisStep {
  order: number;
  title: string;
  detail: string;
  href: string;
  kind: string;
}

interface MissionJarvisAdvisorStrip {
  enabled: boolean;
  headline: string;
  message: string;
  steps: MissionJarvisStep[];
  analytics_href: string;
  research_href: string;
  loops_href: string;
}

interface MissionAgentQualityStrip {
  enabled: boolean;
  status: "healthy" | "warn" | "critical" | "unknown";
  pass_rate_7d_pct: number | null;
  pass_rate_trend: string;
  stuck_sessions: number;
  active_sessions: number;
  operator_hint: string;
  harness_href: string;
  scorecard_href: string;
}

interface MissionWeeklyReflectionHighlight {
  source: "ballroom" | "episodic" | "learning" | "session";
  title: string;
  excerpt: string;
  href: string;
}

interface MissionJarvisWeeklyReflectionStrip {
  enabled: boolean;
  headline: string;
  message: string;
  week_label: string;
  ballroom_post_mortems_7d: number;
  episodic_captures_7d: number;
  sessions_completed_7d: number;
  learning_logs_7d: number;
  highlights: MissionWeeklyReflectionHighlight[];
  hive_mind_href: string;
  episodic_href: string;
  ballroom_href: string;
}

interface MissionWeeklyCompoundStrip {
  enabled: boolean;
  headline: string;
  message: string;
  week_label: string;
  pending_drafts: number;
  brain_pack_gap_count: number;
  last_run_at: string | null;
  hive_mind_href: string;
  evolution_href: string;
  approvals_href: string;
}

interface MissionHomeSnapshot {
  enabled: boolean;
  current_step: ProcessStepId;
  process_steps: ProcessStep[];
  brief_bullets: MissionBriefBullet[];
  next_actions: MissionAction[];
  approvals: MissionApproval[];
  active_sessions: MissionActiveSession[];
  memory_strip?: MissionMemoryStrip;
  step_studios?: MissionStudioEntry[];
  life_os_strip?: MissionLifeOsStrip;
  autopilot_strip?: MissionAutopilotStrip;
  jarvis_advisor_strip?: MissionJarvisAdvisorStrip;
  agent_quality_strip?: MissionAgentQualityStrip;
  jarvis_weekly_reflection_strip?: MissionJarvisWeeklyReflectionStrip;
  weekly_compound_strip?: MissionWeeklyCompoundStrip;
  first_run_complete: boolean;
  links: Record<string, string>;
  rapid_loop_widget_enabled?: boolean;
  sub_swarm_fleet_widget_enabled?: boolean;
  factory_launch_widget_enabled?: boolean;
  catalog_wave_widget_enabled?: boolean;
  revenue_funnel_widget_enabled?: boolean;
}

function MissionHomePanelInner(): JSX.Element | null {
  const { soloMode, personalOsMode } = usePlatform();
  const [snapshot, setSnapshot] = useState<MissionHomeSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!soloMode) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await hiveGet<MissionHomeSnapshot>("solo-operator/mission-home");
      setSnapshot(data);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Mission Home unavailable");
    } finally {
      setLoading(false);
    }
  }, [soloMode]);

  useEffect(() => {
    void reload();
  }, [reload]);

  useIntervalWhenVisible(() => void reload(), COCKPIT_POLL_BOARD_MS);

  if (!soloMode) {
    return null;
  }

  if (loading && !snapshot) {
    return <HivePanelSectionSkeleton label="Loading Mission Home" minHeightClass="min-h-[12rem]" />;
  }

  if (!snapshot?.enabled) {
    return null;
  }

  const newSessionHref = snapshot.links.new_session ?? "/agents#sessions";
  const lifeOs = snapshot.life_os_strip;
  const calendarConnectHref =
    lifeOs?.connect_href ?? snapshot.links.calendar_connect ?? "/integrations?tab=connectors";
  const autopilot = snapshot.autopilot_strip;
  const jarvis = snapshot.jarvis_advisor_strip;
  const agentQuality = snapshot.agent_quality_strip;
  const weeklyReflection = snapshot.jarvis_weekly_reflection_strip;
  const weeklyCompound = snapshot.weekly_compound_strip;

  function qualityTone(status: MissionAgentQualityStrip["status"]): "ok" | "warn" | "err" | "info" {
    if (status === "healthy") return "ok";
    if (status === "warn") return "warn";
    if (status === "critical") return "err";
    return "info";
  }

  function formatEventTime(iso: string | null): string {
    if (!iso) {
      return "All day";
    }
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) {
      return "—";
    }
    return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  }

  return (
    <section
      id="mission-home"
      aria-label="Mission Home"
      className={cn(
        "flex flex-col gap-3",
        "max-lg:gap-3",
        "md:max-lg:grid md:max-lg:grid-cols-2 md:max-lg:gap-4",
      )}
    >
      <ProcessRail
        steps={snapshot.process_steps}
        currentStep={snapshot.current_step}
        compact
      />

      {jarvis?.enabled && jarvis.steps.length > 0 ? (
        <V4Card
          className="md:max-lg:col-span-2 border-pollen/40 shadow-[0_0_24px_rgba(255,184,0,0.12)]"
          data-testid="mission-home-jarvis-advisor"
        >
          <V4CardHeader
            kicker="Advisor"
            title={jarvis.headline}
            description={jarvis.message}
            actions={
              <div className="flex flex-wrap gap-2">
                <Link
                  href={jarvis.analytics_href}
                  className="qs-btn qs-btn--ghost qs-btn--sm"
                >
                  Analyst
                </Link>
                <Link href={jarvis.loops_href} className="qs-btn qs-btn--ghost qs-btn--sm">
                  Loops
                </Link>
              </div>
            }
          />
          <ol className="space-y-2 px-4 pb-4">
            {jarvis.steps.map((step) => (
              <li
                key={`${step.order}-${step.title}`}
                className="rounded-lg border border-pollen/30 bg-black/30 p-3"
              >
                <div className="flex flex-wrap items-start gap-3">
                  <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-pollen/20 font-mono text-sm font-bold text-pollen">
                    {step.order}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Sparkles className="size-3.5 text-pollen" aria-hidden />
                      <span className="text-sm font-semibold text-(--qs-text)">{step.title}</span>
                      <V4Badge tone="info">{step.kind}</V4Badge>
                    </div>
                    <p className="mt-1 text-xs text-(--qs-muted)">{step.detail}</p>
                    <Link
                      href={step.href}
                      className="qs-btn qs-btn--primary qs-btn--sm mt-2 inline-flex gap-1"
                    >
                      Do this
                      <ArrowRight className="size-3.5" aria-hidden />
                    </Link>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </V4Card>
      ) : null}

      {weeklyReflection?.enabled && weeklyReflection.highlights.length > 0 ? (
        <V4Card
          className="md:max-lg:col-span-2 border-cyan/30 shadow-[0_0_20px_rgba(0,255,255,0.08)]"
          data-testid="mission-home-jarvis-weekly-reflection"
        >
          <V4CardHeader
            kicker="Weekly"
            title={weeklyReflection.headline}
            description={weeklyReflection.message}
            actions={
              <div className="flex flex-wrap gap-2">
                <Link
                  href={weeklyReflection.hive_mind_href}
                  className="qs-btn qs-btn--ghost qs-btn--sm inline-flex gap-1"
                >
                  <Brain className="size-3.5" aria-hidden />
                  Hive Mind
                </Link>
                <Link href={weeklyReflection.episodic_href} className="qs-btn qs-btn--ghost qs-btn--sm">
                  Episodic log
                </Link>
              </div>
            }
          />
          {weeklyReflection.week_label ? (
            <p className="px-4 text-xs font-mono text-cyan/80">{weeklyReflection.week_label}</p>
          ) : null}
          <div className="flex flex-wrap gap-2 px-4 pt-2">
            {weeklyReflection.ballroom_post_mortems_7d > 0 ? (
              <V4Badge tone="info">{weeklyReflection.ballroom_post_mortems_7d} post-mortem</V4Badge>
            ) : null}
            {weeklyReflection.episodic_captures_7d > 0 ? (
              <V4Badge tone="purple">{weeklyReflection.episodic_captures_7d} episodic</V4Badge>
            ) : null}
            {weeklyReflection.sessions_completed_7d > 0 ? (
              <V4Badge tone="ok">{weeklyReflection.sessions_completed_7d} sessions</V4Badge>
            ) : null}
          </div>
          <ul className="space-y-2 px-4 pb-4 pt-3">
            {weeklyReflection.highlights.map((item) => (
              <li
                key={`${item.source}-${item.title}`}
                className="rounded-lg border border-cyan/20 bg-black/30 p-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-(--qs-text)">{item.title}</span>
                  <V4Badge tone="info">{item.source}</V4Badge>
                </div>
                <p className="mt-1 text-xs text-(--qs-muted)">{item.excerpt}</p>
                <Link href={item.href} className="qs-btn qs-btn--ghost qs-btn--sm mt-2 inline-flex gap-1">
                  Review
                  <ArrowRight className="size-3.5" aria-hidden />
                </Link>
              </li>
            ))}
          </ul>
        </V4Card>
      ) : null}

      {weeklyCompound?.enabled ? (
        <V4Card className="md:max-lg:col-span-2" data-testid="mission-home-weekly-compound">
          <V4CardHeader
            kicker="Compound"
            title={weeklyCompound.headline}
            description={weeklyCompound.message}
            actions={
              <div className="flex flex-wrap gap-2">
                {weeklyCompound.pending_drafts > 0 ? (
                  <Link
                    href={weeklyCompound.approvals_href ?? "/cockpit#approvals"}
                    className="qs-btn qs-btn--primary qs-btn--sm inline-flex gap-1"
                    data-testid="mission-home-weekly-compound-cockpit"
                  >
                    <Shield className="size-3.5" aria-hidden />
                    Cockpit
                  </Link>
                ) : null}
                <Link
                  href={weeklyCompound.evolution_href}
                  className="qs-btn qs-btn--ghost qs-btn--sm inline-flex gap-1"
                >
                  <Brain className="size-3.5" aria-hidden />
                  Evolution
                </Link>
                <Link href={weeklyCompound.hive_mind_href} className="qs-btn qs-btn--ghost qs-btn--sm">
                  Hive Mind
                </Link>
              </div>
            }
          />
          {weeklyCompound.week_label ? (
            <p className="px-4 text-xs font-mono text-cyan/80">{weeklyCompound.week_label}</p>
          ) : null}
          <div className="flex flex-wrap gap-2 px-4 pb-4 pt-2">
            {weeklyCompound.pending_drafts > 0 ? (
              <V4Badge tone="warn">{weeklyCompound.pending_drafts} draft(s)</V4Badge>
            ) : null}
            {weeklyCompound.brain_pack_gap_count > 0 ? (
              <V4Badge tone="info">{weeklyCompound.brain_pack_gap_count} Brain Pack gap(s)</V4Badge>
            ) : null}
          </div>
        </V4Card>
      ) : null}

      {agentQuality?.enabled ? (
        <V4Card className="md:max-lg:col-span-2" data-testid="mission-home-agent-quality">
          <V4CardHeader
            kicker="Quality"
            title="Agent scorecard"
            description="Simulation pass rate + session health — verify-first harness."
            actions={
              <Link href={agentQuality.harness_href} className="qs-btn qs-btn--ghost qs-btn--sm">
                Review loop
              </Link>
            }
          />
          <div className="flex flex-wrap gap-2 px-4 pb-4">
            <V4Badge tone={qualityTone(agentQuality.status)}>{agentQuality.status}</V4Badge>
            {agentQuality.pass_rate_7d_pct != null ? (
              <V4Badge tone="info">{agentQuality.pass_rate_7d_pct}% pass (7d)</V4Badge>
            ) : null}
            {agentQuality.stuck_sessions > 0 ? (
              <V4Badge tone="warn">{agentQuality.stuck_sessions} stuck</V4Badge>
            ) : null}
            {agentQuality.active_sessions > 0 ? (
              <V4Badge tone="purple">{agentQuality.active_sessions} running</V4Badge>
            ) : null}
          </div>
          <p className="px-4 pb-4 text-sm text-(--qs-text-2)">{agentQuality.operator_hint}</p>
        </V4Card>
      ) : null}

      {snapshot.rapid_loop_widget_enabled ? (
        <div className="md:max-lg:col-span-2" data-testid="mission-home-rapid-loop">
          <RapidLoopWidget eager />
        </div>
      ) : null}

      {snapshot.sub_swarm_fleet_widget_enabled ? (
        <div className="md:max-lg:col-span-2" data-testid="mission-home-sub-swarm-fleet">
          <SubSwarmFleetWidget eager />
        </div>
      ) : null}

      {snapshot.revenue_funnel_widget_enabled && !personalOsMode ? (
        <div className="md:max-lg:col-span-2" data-testid="mission-home-revenue-funnel">
          <RevenueFunnelStrip eager />
        </div>
      ) : null}

      {snapshot.factory_launch_widget_enabled && !personalOsMode ? (
        <div className="md:max-lg:col-span-2" data-testid="mission-home-factory-launch">
          <FactoryLaunchWidget eager />
        </div>
      ) : null}

      {snapshot.catalog_wave_widget_enabled && !personalOsMode ? (
        <div className="md:max-lg:col-span-2" data-testid="mission-home-catalog-wave">
          <CatalogWaveWidget eager />
        </div>
      ) : null}

      {snapshot.step_studios && snapshot.step_studios.length > 0 ? (
        <div className="flex flex-wrap gap-2 max-lg:px-0">
          {snapshot.step_studios.map((studio) => (
            <Link
              key={studio.id}
              href={studio.href}
              className="qs-btn qs-btn--ghost qs-btn--sm min-h-[44px] gap-1 border border-(--qs-border)/50"
              title={studio.detail}
            >
              {studio.title}
              <ArrowRight className="size-3.5" aria-hidden />
            </Link>
          ))}
        </div>
      ) : null}

      {err ? (
        <p className="text-xs text-[#FF3366]" role="alert">
          {err}
        </p>
      ) : null}

      {autopilot?.enabled ? (
        <V4Card className="md:max-lg:col-span-2" data-testid="mission-home-autopilot">
          <V4CardHeader
            kicker="Background"
            title="Autopilot"
            description="My 3 Bees + Four Lanes cron — simulate-first digests."
            actions={
              <div className="flex flex-wrap gap-2">
                <Link href={autopilot.harness_href} className="qs-btn qs-btn--ghost qs-btn--sm">
                  Harness
                </Link>
                <Link href={autopilot.four_lanes_href} className="qs-btn qs-btn--ghost qs-btn--sm">
                  Lanes
                </Link>
                {autopilot.digest_pending > 0 ? (
                  <Link href={autopilot.digest_href} className="qs-btn qs-btn--primary qs-btn--sm">
                    Digest ({autopilot.digest_pending})
                  </Link>
                ) : null}
              </div>
            }
          />
          <p className="px-4 text-sm text-(--qs-text-2)">{autopilot.message}</p>
          <div className="flex flex-wrap gap-2 px-4 pb-4 pt-3">
            <V4Badge tone="info">
              My 3 Bees {autopilot.trio_bound}/{autopilot.trio_total}
            </V4Badge>
            <V4Badge tone="purple">
              Four Lanes {autopilot.four_lanes_active}/{autopilot.four_lanes_total}
            </V4Badge>
            {autopilot.cron_lane_count > 0 ? (
              <V4Badge tone="ok">{autopilot.cron_lane_count} cron</V4Badge>
            ) : null}
          </div>
          <ul className="grid gap-2 px-4 pb-4 max-lg:grid-cols-1 md:max-lg:grid-cols-2 lg:grid-cols-3">
            {autopilot.lanes.map((lane) => (
              <li
                key={`${lane.group}-${lane.id}`}
                className="rounded-lg border border-(--qs-border)/50 bg-black/20 p-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Zap
                    className={cn(
                      "size-3.5",
                      lane.status === "active" ? "text-[#00FF88]" : "text-(--qs-muted)",
                    )}
                    aria-hidden
                  />
                  <span className="text-xs font-semibold text-(--qs-text)">{lane.label}</span>
                  <V4Badge
                    tone={
                      lane.status === "active"
                        ? "ok"
                        : lane.status === "missing"
                          ? "warn"
                          : "info"
                    }
                  >
                    {lane.status}
                  </V4Badge>
                  {lane.group === "four_lane" && lane.schedule_cron ? (
                    <span className="font-mono text-[10px] text-(--qs-muted)">{lane.schedule_cron}</span>
                  ) : null}
                </div>
                {lane.detail ? (
                  <p className="mt-1 line-clamp-2 text-[11px] text-(--qs-muted)">{lane.detail}</p>
                ) : null}
              </li>
            ))}
          </ul>
        </V4Card>
      ) : autopilot && !autopilot.routines_enabled ? (
        <V4Card className="md:max-lg:col-span-2" data-testid="mission-home-autopilot">
          <V4CardHeader kicker="Background" title="Autopilot" description="Routines disabled." />
          <p className="px-4 pb-4 text-sm text-(--qs-muted)">{autopilot.message}</p>
        </V4Card>
      ) : null}

      <div className="flex flex-col gap-3 md:max-lg:contents">
        <V4Card className="md:max-lg:col-span-1">
          <V4CardHeader
            kicker="Today"
            title="Brief"
            description="Verified trio lanes and tech health — simulate-first."
            hint={sectionHintNode("missionHome")}
            actions={<HiveRefreshButton busy={loading} onClick={() => void reload()} />}
          />
          <ul className="space-y-2 px-4 pb-4">
            {snapshot.brief_bullets.map((bullet) => (
              <li key={bullet.text} className="flex gap-2 text-sm text-(--qs-text-2)">
                <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-cyan" aria-hidden />
                <span>{bullet.text}</span>
              </li>
            ))}
          </ul>
        </V4Card>

        {lifeOs?.enabled ? (
          <V4Card className="md:max-lg:col-span-1" data-testid="mission-home-life-os">
            <V4CardHeader
              kicker="Life OS"
              title="Calendar"
              description="Google Calendar blocks — plan work around meetings."
              actions={
                !lifeOs.connected ? (
                  <Link href={calendarConnectHref} className="qs-btn qs-btn--ghost qs-btn--sm">
                    Connect
                  </Link>
                ) : null
              }
            />
            {!lifeOs.connected ? (
              <div className="px-4 pb-4">
                <p className="text-sm text-(--qs-muted)">{lifeOs.message}</p>
                <Link
                  href={calendarConnectHref}
                  className="qs-btn qs-btn--primary qs-btn--sm mt-3 inline-flex gap-1"
                >
                  <CalendarClock className="size-3.5" aria-hidden />
                  Connect Google Calendar
                </Link>
              </div>
            ) : lifeOs.events.length === 0 ? (
              <p className="px-4 pb-4 text-sm text-(--qs-muted)">{lifeOs.message}</p>
            ) : (
              <ul className="space-y-2 px-4 pb-4">
                {lifeOs.events.map((event) => (
                  <li
                    key={event.id}
                    className="rounded-lg border border-(--qs-border)/50 bg-black/20 p-3"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <CalendarClock className="size-4 text-pollen" aria-hidden />
                      <span className="font-mono text-xs text-pollen">{formatEventTime(event.start_at)}</span>
                      <span className="text-sm font-semibold text-(--qs-text)">{event.title}</span>
                    </div>
                    {event.detail ? (
                      <p className="mt-1 text-xs text-(--qs-muted)">{event.detail}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </V4Card>
        ) : null}

        <V4Card className="md:max-lg:col-span-1">
          <V4CardHeader
            kicker="Next"
            title="Actions"
            description="Top 3 priorities from your daily plan."
          />
          {snapshot.next_actions.length === 0 ? (
            <p className="px-4 pb-4 text-sm text-(--qs-muted)">
              No queued actions —{" "}
              <Link href={newSessionHref} className="text-cyan underline">
                start a session
              </Link>
              .
            </p>
          ) : (
            <ul className="space-y-2 px-4 pb-4">
              {snapshot.next_actions.map((action) => (
                <li
                  key={action.id}
                  className="rounded-lg border border-(--qs-border)/50 bg-black/20 p-3"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-(--qs-text)">{action.title}</span>
                    <V4Badge tone={action.priority === 1 ? "warn" : "info"}>P{action.priority}</V4Badge>
                  </div>
                  <p className="mt-1 text-xs text-(--qs-muted)">{action.detail}</p>
                  {action.href ? (
                    <Link
                      href={action.href}
                      className="qs-btn qs-btn--primary qs-btn--sm mt-2 inline-flex gap-1"
                    >
                      Open
                      <ArrowRight className="size-3.5" aria-hidden />
                    </Link>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </V4Card>
      </div>

      <V4Card className="md:max-lg:col-span-2">
        <V4CardHeader
          kicker="Memory"
          title="Brain Pack"
          description="SOUL · MEMORY · USER — human-editable Queen context."
          hint={sectionHintNode("missionHomeMemory")}
          actions={
            <Link href={snapshot.links.knowledge ?? "/knowledge#memory"} className="qs-btn qs-btn--ghost qs-btn--sm">
              Edit
            </Link>
          }
        />
        <div
          className="mx-4 mb-3 h-2 overflow-hidden rounded-full bg-black/40"
          role="progressbar"
          aria-valuenow={snapshot.memory_strip?.usage_pct ?? 0}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Brain Pack token usage"
        >
          <div
            className="h-full rounded-full bg-linear-to-r from-cyan to-pollen transition-[width] duration-500"
            style={{ width: `${snapshot.memory_strip?.usage_pct ?? 0}%` }}
          />
        </div>
        <p className="mb-3 px-4 text-[11px] text-(--qs-muted)">
          {snapshot.memory_strip?.total_chars ?? 0} / {snapshot.memory_strip?.max_chars ?? 0} chars (
          {snapshot.memory_strip?.usage_pct ?? 0}%)
        </p>
        <div className="grid gap-2 px-4 pb-4 max-lg:grid-cols-1 md:max-lg:grid-cols-3">
          {(snapshot.memory_strip?.layers ?? []).map((layer) => (
            <Link
              key={layer.id}
              href={layer.href}
              className="block rounded-lg border border-(--qs-border)/50 bg-black/20 p-3 transition hover:border-cyan/40 min-h-[44px]"
            >
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-semibold text-cyan">{layer.label}</span>
                {layer.filled ? <V4Badge tone="ok">Ready</V4Badge> : <V4Badge tone="warn">Empty</V4Badge>}
              </div>
              <p className="mt-1 line-clamp-2 text-xs text-(--qs-muted)">{layer.preview}</p>
            </Link>
          ))}
        </div>
      </V4Card>

      <div className="flex flex-col gap-3 md:max-lg:contents">
        <V4Card className="md:max-lg:col-span-1">
          <V4CardHeader
            kicker="Verify"
            title="Approvals"
            description="Simulate-first gates — nothing live without you."
            actions={
              snapshot.approvals.length > 0 ? (
                <Link
                  href={snapshot.links.approvals ?? "/cockpit#approvals"}
                  className="qs-btn qs-btn--ghost qs-btn--sm"
                >
                  View all
                </Link>
              ) : null
            }
          />
          {snapshot.approvals.length === 0 ? (
            <p className="flex items-center gap-2 px-4 pb-4 text-sm text-(--qs-muted)">
              <Shield className="size-4 text-[#00FF88]" aria-hidden />
              Inbox clear — verified path only.
            </p>
          ) : (
            <ul className="space-y-2 px-4 pb-4">
              {snapshot.approvals.slice(0, 5).map((row) => (
                <li key={row.id}>
                  <Link
                    href={row.href}
                    className="block rounded-lg border border-(--qs-border)/50 bg-black/20 p-3 transition hover:border-pollen/40"
                  >
                    <span className="text-sm font-semibold text-(--qs-text)">{row.title}</span>
                    <p className="mt-1 text-xs text-(--qs-muted)">{row.detail}</p>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </V4Card>

        <V4Card className="md:max-lg:col-span-1">
          <V4CardHeader
            kicker="Work"
            title="Active sessions"
            description="Supervisor missions in flight."
          />
          {snapshot.active_sessions.length === 0 ? (
            <div className="px-4 pb-4">
              <p className="text-sm text-(--qs-muted)">No active sessions.</p>
              <Link href={newSessionHref} className="qs-btn qs-btn--primary qs-btn--sm mt-3 inline-flex gap-1">
                New session
                <ArrowRight className="size-3.5" aria-hidden />
              </Link>
            </div>
          ) : (
            <ul className="space-y-2 px-4 pb-4">
              {snapshot.active_sessions.map((row) => (
                <li key={row.session_id}>
                  <Link
                    href={row.href}
                    className="block rounded-lg border border-(--qs-border)/50 bg-black/20 p-3 transition hover:border-cyan/40"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-(--qs-text)">{row.goal || "Session"}</span>
                      <V4Badge tone="info">{row.loop_chip}</V4Badge>
                      {row.status === "needs_input" ? (
                        <V4Badge tone="warn">Needs input</V4Badge>
                      ) : (
                        <V4Badge tone="purple">{row.progress_pct}%</V4Badge>
                      )}
                    </div>
                    {row.status === "running" ? (
                      <p className="mt-2 flex items-center gap-2 text-xs text-cyan">
                        <Loader2 className="size-3 animate-spin" aria-hidden />
                        {row.progress_label}
                      </p>
                    ) : null}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </V4Card>
      </div>

      {!snapshot.first_run_complete ? (
        <p className="text-center text-xs text-pollen lg:hidden">
          <Link href="/agents#first-run-wizard" className="underline">
            Finish first-run setup
          </Link>{" "}
          to unlock the full daily loop.
        </p>
      ) : null}
    </section>
  );
}

export const MissionHomePanel = memo(MissionHomePanelInner);
