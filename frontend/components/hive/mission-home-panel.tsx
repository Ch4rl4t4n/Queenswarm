"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, Loader2, Shield } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";

import { HivePanelSectionSkeleton } from "@/components/hive/hive-panel-section-skeleton";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { ProcessRail, type ProcessStep, type ProcessStepId } from "@/components/hive/process-rail";
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
  href: string;
}

interface MissionHomeSnapshot {
  enabled: boolean;
  current_step: ProcessStepId;
  process_steps: ProcessStep[];
  brief_bullets: MissionBriefBullet[];
  next_actions: MissionAction[];
  approvals: MissionApproval[];
  active_sessions: MissionActiveSession[];
  first_run_complete: boolean;
  links: Record<string, string>;
}

function MissionHomePanelInner(): JSX.Element | null {
  const { soloMode } = usePlatform();
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

      {err ? (
        <p className="text-xs text-[#FF3366]" role="alert">
          {err}
        </p>
      ) : null}

      <div className="flex flex-col gap-3 md:max-lg:contents">
        <V4Card className="md:max-lg:col-span-1">
          <V4CardHeader
            kicker="Today"
            title="Brief"
            description="Verified trio lanes and tech health — simulate-first."
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
                      {row.status === "needs_input" ? (
                        <V4Badge tone="warn">Needs input</V4Badge>
                      ) : (
                        <V4Badge tone="info">{row.progress_label}</V4Badge>
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
