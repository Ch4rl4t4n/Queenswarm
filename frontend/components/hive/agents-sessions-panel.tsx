"use client";

import type { JSX } from "react";

import Link from "next/link";
import { CheckCircle2, Play, Plus, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import { toast } from "sonner";

import { BrowserHarnessPanel } from "@/components/hive/browser-harness-panel";
import { InfoHint } from "@/components/hive/info-hint";
import { VoiceSessionControls } from "@/components/hive/voice-session-controls";
import { AgentSessionDetailDrawer } from "@/components/hive/agent-session-detail-drawer";
import { AgentSessionEventLog } from "@/components/hive/agent-session-event-log";
import { AgentSessionInteractForm } from "@/components/hive/agent-session-interact-form";
import { QsSelect } from "@/components/ui/qs-select";
import {
  V4Badge,
  V4Card,
  V4CardHeader,
  V4IconAgents,
  V4IconBolt,
  V4Stat,
} from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { integrationsTabHref } from "@/lib/integrations-routes";
import type {
  SupervisorControlSummaryRow,
  SupervisorRoutineRow,
  SupervisorSessionEventRow,
  SupervisorSessionRow,
} from "@/lib/hive-types";
import { runtimeModeLabel, sessionStatusTone } from "@/lib/supervisor-session";

interface CreateSessionPayload {
  goal: string;
  runtime_mode: "inprocess" | "durable";
  roles: string[];
  retrieval_contract: string;
  skills: string[];
}

const ROLE_OPTIONS = ["researcher", "coder", "browser_operator", "critic", "designer"] as const;
type SessionStatusFilter = "all" | "running" | "needs_input" | "completed" | "failed" | "queued";

function shortSessionId(id: string): string {
  const tail = id.replace(/-/g, "").slice(-4).toUpperCase();
  return `S-${tail}`;
}

function sessionRuntimeLabel(session: SupervisorSessionRow): string {
  const startRaw = session.started_at ?? session.created_at;
  const start = new Date(startRaw).getTime();
  if (Number.isNaN(start)) {
    return "—";
  }
  const end = session.completed_at ? new Date(session.completed_at).getTime() : Date.now();
  const sec = Math.max(0, Math.floor((end - start) / 1000));
  if (sec < 60) {
    return `${sec}s`;
  }
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

function sessionStatusBadgeTone(status: string): "info" | "warn" | "ok" | "gold" {
  if (status === "running") {
    return "info";
  }
  if (status === "needs_input") {
    return "warn";
  }
  if (status === "completed" || status === "approved") {
    return "ok";
  }
  return "gold";
}

interface AgentsSessionsPanelProps {
  variant?: "default" | "v4";
}

export function AgentsSessionsPanel({ variant = "default" }: AgentsSessionsPanelProps): JSX.Element {
  const [goal, setGoal] = useState("");
  const [runtimeMode, setRuntimeMode] = useState<"inprocess" | "durable">("inprocess");
  const [busy, setBusy] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [reviewBusy, setReviewBusy] = useState<string | null>(null);
  const [routineName, setRoutineName] = useState("");
  const [routineGoal, setRoutineGoal] = useState("");
  const [routineInterval, setRoutineInterval] = useState(3600);
  const [routineBusy, setRoutineBusy] = useState(false);
  const [sessionQuery, setSessionQuery] = useState("");
  const [sessionStatusFilter, setSessionStatusFilter] = useState<SessionStatusFilter>("all");

  const {
    data: sessions = [],
    error,
    isLoading,
    mutate,
  } = useSWR<SupervisorSessionRow[]>(
    "hive/agent-sessions",
    () => hiveGet<SupervisorSessionRow[]>("agents/sessions?limit=40"),
    { refreshInterval: 5000 },
  );

  const { data: routines = [], mutate: mutateRoutines } = useSWR<SupervisorRoutineRow[]>(
    "hive/agent-routines",
    () => hiveGet<SupervisorRoutineRow[]>("agents/routines?limit=40"),
    { refreshInterval: 10_000 },
  );
  const { data: summary } = useSWR<SupervisorControlSummaryRow>(
    "hive/agent-sessions-summary",
    () => hiveGet<SupervisorControlSummaryRow>("agents/sessions/summary"),
    { refreshInterval: 5000 },
  );

  const selected = useMemo(
    () => sessions.find((session) => session.id === selectedSessionId) ?? null,
    [sessions, selectedSessionId],
  );
  const filteredSessions = useMemo(() => {
    const q = sessionQuery.trim().toLowerCase();
    return sessions.filter((session) => {
      if (sessionStatusFilter !== "all" && session.status !== sessionStatusFilter) {
        return false;
      }
      if (!q) {
        return true;
      }
      return (
        session.goal.toLowerCase().includes(q) ||
        session.status.toLowerCase().includes(q) ||
        session.runtime_mode.toLowerCase().includes(q)
      );
    });
  }, [sessions, sessionQuery, sessionStatusFilter]);

  useEffect(() => {
    if (filteredSessions.length === 0) {
      if (selectedSessionId !== null) {
        setSelectedSessionId(null);
      }
      return;
    }
    if (!selectedSessionId || !filteredSessions.some((session) => session.id === selectedSessionId)) {
      setSelectedSessionId(filteredSessions[0]?.id ?? null);
    }
  }, [filteredSessions, selectedSessionId]);

  const {
    data: events = [],
    mutate: mutateEvents,
    isLoading: eventsLoading,
  } = useSWR<SupervisorSessionEventRow[]>(
    selected ? `hive/agent-sessions/${selected.id}/events` : null,
    () => hiveGet<SupervisorSessionEventRow[]>(`agents/sessions/${selected?.id}/events?limit=120`),
    { refreshInterval: 4000 },
  );

  async function createSession(): Promise<void> {
    const payload: CreateSessionPayload = {
      goal: goal.trim(),
      runtime_mode: runtimeMode,
      roles: [...ROLE_OPTIONS],
      retrieval_contract: "customer_history+policy+last_3_tasks",
      skills: ["context", "decide", "tdd"],
    };
    if (payload.goal.length < 4) {
      toast.error("Goal is too short.");
      return;
    }
    setBusy(true);
    try {
      const created = await hivePostJson<SupervisorSessionRow>("agents/sessions", payload);
      setGoal("");
      setSelectedSessionId(created.id);
      await mutate();
      toast.success("Supervisor session created.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Session create failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function controlSession(sessionId: string, action: "pause" | "resume" | "stop"): Promise<void> {
    try {
      await hivePostJson(`agents/sessions/${sessionId}/control`, { action });
      await mutate();
      toast.success(`Session ${action} applied.`);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Control failed";
      toast.error(msg);
    }
  }

  async function reviewSession(sessionId: string, decision: "approve" | "reject"): Promise<void> {
    setReviewBusy(sessionId);
    try {
      await hivePostJson(`agents/sessions/${sessionId}/review`, { decision });
      await mutate();
      toast.success(`Session ${decision}d.`);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Review failed";
      toast.error(msg);
    } finally {
      setReviewBusy(null);
    }
  }

  async function createRoutine(): Promise<void> {
    if (routineName.trim().length < 2 || routineGoal.trim().length < 4) {
      toast.error("Routine name/goal is too short.");
      return;
    }
    setRoutineBusy(true);
    try {
      await hivePostJson("agents/routines", {
        name: routineName.trim(),
        goal_template: routineGoal.trim(),
        schedule_kind: "interval",
        interval_seconds: Math.max(60, routineInterval),
        runtime_mode: "durable",
        roles: ["researcher", "critic"],
        retrieval_contract: "customer_history+policy+last_3_tasks",
        skills: ["context", "diagnose"],
      });
      setRoutineName("");
      setRoutineGoal("");
      setRoutineInterval(3600);
      await mutateRoutines();
      toast.success("Routine created.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Routine create failed";
      toast.error(msg);
    } finally {
      setRoutineBusy(false);
    }
  }

  async function triggerRoutine(routineId: string): Promise<void> {
    try {
      await hivePostJson(`agents/routines/${routineId}/trigger`, {});
      toast.success("Routine triggered.");
      await Promise.all([mutate(), mutateRoutines()]);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Routine trigger failed";
      toast.error(msg);
    }
  }

  if (error) {
    return (
      <V4Card>
        <p className="text-sm text-(--qs-red)">
          Session panel unavailable ({error.message}). Enable dynamic supervisor feature flags first.
        </p>
      </V4Card>
    );
  }

  const isV4 = variant === "v4";
  const Shell = isV4 ? V4Card : "section";
  const shellClass = isV4 ? undefined : "rounded-3xl qs-rim-cyan-soft bg-[#0a0f18]/80 p-5 md:p-6";

  return (
    <Shell id="sessions" className={shellClass}>
      {isV4 ? (
        <V4CardHeader
          title="Dynamic supervisor sessions"
          description="Spawn sub-agents, track statuses, and interact through shared memory logs."
          actions={
            <>
              <Link href={integrationsTabHref("hub")} className="qs-btn qs-btn--ghost qs-btn--sm">
                Tool hub
              </Link>
              <Link href="/ballroom" className="qs-btn qs-btn--ghost qs-btn--sm">
                Open Ballroom
              </Link>
            </>
          }
        />
      ) : (
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-zinc-100">Dynamic Supervisor Sessions</h2>
              <InfoHint
                title="Dynamic Supervisor Sessions"
                description="Control panel for Supervisor lifecycle, review decisions, and sub-agent orchestration."
                options={["Create session", "Pause/Resume/Stop", "Approve/Reject", "Live event log"]}
              />
            </div>
            <p className="mt-1 text-xs text-zinc-400">
              Spawn sub-agents, track statuses, and interact through shared memory logs.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
              <Link href={integrationsTabHref("hub")} className="qs-btn qs-btn--ghost qs-btn--sm">
              Tool Hub
            </Link>
            <Link href="/ballroom" className="qs-btn qs-btn--ghost qs-btn--sm">
              Open Ballroom
            </Link>
          </div>
        </div>
      )}

      {isV4 ? (
        <div className="v4-stat-grid">
          <V4Stat label="Sessions total" value={summary?.sessions_total ?? 0} icon={V4IconAgents} iconTone="purple" />
          <V4Stat
            label="Running / needs input"
            value={`${summary?.running_sessions ?? 0} / ${summary?.needs_input_sessions ?? 0}`}
            icon={V4IconBolt}
            valueVariant="text"
          />
          <V4Stat
            label="Routines total"
            value={summary?.routines_total ?? 0}
            icon={RefreshCw}
            iconTone="cyan"
            valueVariant="text"
          />
          <V4Stat
            label="Active / due"
            value={`${summary?.active_routines ?? 0} / ${summary?.due_routines ?? 0}`}
            icon={CheckCircle2}
            iconTone="green"
            valueVariant="text"
          />
        </div>
      ) : (
        <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border border-[color:var(--qs-border)] bg-black/25 p-3 text-xs text-zinc-300">
            <p className="text-zinc-500">Sessions total</p>
            <p className="mt-1 text-base font-semibold text-zinc-100">{summary?.sessions_total ?? 0}</p>
          </div>
          <div className="rounded-xl border border-[color:var(--qs-border)] bg-black/25 p-3 text-xs text-zinc-300">
            <p className="text-zinc-500">Running / Needs input</p>
            <p className="mt-1 text-base font-semibold text-zinc-100">
              {summary?.running_sessions ?? 0} / {summary?.needs_input_sessions ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-[color:var(--qs-border)] bg-black/25 p-3 text-xs text-zinc-300">
            <p className="text-zinc-500">Routines total</p>
            <p className="mt-1 text-base font-semibold text-zinc-100">{summary?.routines_total ?? 0}</p>
          </div>
          <div className="rounded-xl border border-[color:var(--qs-border)] bg-black/25 p-3 text-xs text-zinc-300">
            <p className="text-zinc-500">Active / Due</p>
            <p className="mt-1 text-base font-semibold text-zinc-100">
              {summary?.active_routines ?? 0} / {summary?.due_routines ?? 0}
            </p>
          </div>
        </div>
      )}

      <div className={isV4 ? "mt-5" : "mt-4"}>
        <BrowserHarnessPanel />
      </div>

      <div
        className={
          isV4
            ? "mt-4 flex flex-col gap-3 md:flex-row md:items-center"
            : "mt-4 grid gap-3 rounded-2xl border border-[color:var(--qs-border)] bg-black/30 p-4 md:grid-cols-[1fr_auto_auto]"
        }
      >
        <input
          className="qs-input min-w-0 flex-1"
          placeholder="Session goal — e.g. investigate onboarding drop-off…"
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
        />
        {!isV4 ? (
          <InfoHint
            title="Session goal"
            description="Primary session objective. The more specific the goal, the better the output quality."
            options={["One mission per session", "Include constraints", "Define expected outcome"]}
          />
        ) : null}
        <QsSelect
          className="w-full md:w-40"
          value={runtimeMode}
          onValueChange={(next) => setRuntimeMode(next as "inprocess" | "durable")}
          options={[
            { value: "inprocess", label: "in-process" },
            { value: "durable", label: "durable" },
          ]}
        />
        {!isV4 ? (
          <InfoHint
            title="Runtime mode"
            description="Selects execution mode for the Supervisor session."
            options={["in-process: faster flow", "durable: more robust long-running flow"]}
          />
        ) : null}
        <button
          type="button"
          className="qs-btn qs-btn--primary qs-btn--sm w-full gap-2 disabled:opacity-40 md:w-auto"
          disabled={busy}
          onClick={() => void createSession()}
        >
          <Play className="h-4 w-4" aria-hidden />
          {busy ? "Creating…" : "Create session"}
        </button>
      </div>

      <div className={isV4 ? "mt-4" : "mt-3"}>
        <VoiceSessionControls
          compact
          label="Supervisor voice command"
          onTranscript={(text) => {
            setGoal((prev) => (prev.trim() ? `${prev.trim()} ${text}` : text));
          }}
        />
      </div>

      <div className={isV4 ? "mt-5 flex flex-col gap-3 md:flex-row" : "mt-4 grid gap-2 rounded-2xl border border-zinc-800 bg-black/20 p-3 md:grid-cols-[1fr_180px]"}>
        <input
          className="qs-input min-w-0 flex-1"
          placeholder="Filter sessions by goal / status / runtime…"
          value={sessionQuery}
          onChange={(event) => setSessionQuery(event.target.value)}
        />
        <QsSelect
          className="w-full md:w-40"
          value={sessionStatusFilter}
          onValueChange={(next) => setSessionStatusFilter(next as SessionStatusFilter)}
          options={[
            { value: "all", label: "all statuses" },
            { value: "running", label: "running" },
            { value: "needs_input", label: "needs_input" },
            { value: "queued", label: "queued" },
            { value: "completed", label: "completed" },
            { value: "failed", label: "failed" },
          ]}
        />
      </div>

      <div className="mt-4 flex flex-col gap-3">
        {isLoading ? (
          <p className="text-sm text-(--qs-text-3)">Loading sessions…</p>
        ) : filteredSessions.length === 0 ? (
          <p className="text-sm text-(--qs-text-3)">No sessions yet.</p>
        ) : (
          filteredSessions.map((session) =>
            isV4 ? (
              <div key={session.id} className="v4-session-row">
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex flex-wrap items-center gap-2">
                    <span className="font-(family-name:--font-jetbrains-mono) text-[11px] text-(--qs-text-3)">
                      {shortSessionId(session.id)}
                    </span>
                    <V4Badge tone={sessionStatusBadgeTone(session.status)}>
                      {session.status.replaceAll("_", " ")}
                    </V4Badge>
                  </div>
                  <p className="text-sm font-medium text-(--qs-text)">{session.goal}</p>
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  <span className="text-xs text-(--qs-text-3)">
                    {sessionRuntimeLabel(session)} · {session.sub_agents.length} agents
                  </span>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    onClick={() => setSelectedSessionId(session.id)}
                  >
                    Open
                  </button>
                  <Link href={`/ballroom?session=${encodeURIComponent(session.id)}`} className="qs-btn qs-btn--ghost qs-btn--sm">
                    Ballroom
                  </Link>
                  <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void controlSession(session.id, "pause")}>
                    Pause
                  </button>
                  <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void controlSession(session.id, "resume")}>
                    Resume
                  </button>
                  <button type="button" className="qs-btn qs-btn--danger qs-btn--sm" onClick={() => void controlSession(session.id, "stop")}>
                    Stop
                  </button>
                  {session.status === "needs_input" ? (
                    <>
                      <button
                        type="button"
                        className="qs-btn qs-btn--green qs-btn--sm"
                        disabled={reviewBusy === session.id}
                        onClick={() => void reviewSession(session.id, "approve")}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className="qs-btn qs-btn--danger qs-btn--sm"
                        disabled={reviewBusy === session.id}
                        onClick={() => void reviewSession(session.id, "reject")}
                      >
                        Reject
                      </button>
                    </>
                  ) : null}
                </div>
              </div>
            ) : (
              <div key={session.id} className="rounded-2xl border border-zinc-800 bg-black/25 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-zinc-100">{session.goal}</p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {runtimeModeLabel(session.runtime_mode)} · {session.status} · {session.sub_agents.length} sub-agents
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <span className={`qs-pill qs-pill--active-${sessionStatusTone(session.status)}`}>{session.status}</span>
                    {session.status === "needs_input" ? (
                      <span className="rounded-full border border-[#FFB800]/40 bg-[#FFB800]/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.08em] text-[#FFB800]">
                        needs input
                      </span>
                    ) : null}
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm"
                      onClick={() => setSelectedSessionId(session.id)}
                    >
                      Open
                    </button>
                    <Link href={`/ballroom?session=${encodeURIComponent(session.id)}`} className="qs-btn qs-btn--ghost qs-btn--sm">
                      Ballroom
                    </Link>
                    <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void controlSession(session.id, "pause")}>
                      Pause
                    </button>
                    <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void controlSession(session.id, "resume")}>
                      Resume
                    </button>
                    <button type="button" className="qs-btn qs-btn--danger qs-btn--sm" onClick={() => void controlSession(session.id, "stop")}>
                      Stop
                    </button>
                    <button
                      type="button"
                      className="qs-btn qs-btn--green qs-btn--sm"
                      disabled={reviewBusy === session.id}
                      onClick={() => void reviewSession(session.id, "approve")}
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="qs-btn qs-btn--danger qs-btn--sm"
                      disabled={reviewBusy === session.id}
                      onClick={() => void reviewSession(session.id, "reject")}
                    >
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            ),
          )
        )}
      </div>

      {selected ? (
        <div className={isV4 ? "v4-learning-panel mt-6" : "mt-6 space-y-3 rounded-2xl border border-[color:var(--qs-border)] bg-black/25 p-4"}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--qs-text-3)">Live event log</p>
              <p className="mt-1 text-xs text-(--qs-text-3)">
                {selected.goal} · {selected.status} · {runtimeModeLabel(selected.runtime_mode)}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href={`/ballroom?session=${encodeURIComponent(selected.id)}`} className="qs-btn qs-btn--ghost qs-btn--sm">
                Open in Ballroom
              </Link>
              <button
                type="button"
                className="qs-btn qs-btn--green qs-btn--sm"
                disabled={reviewBusy === selected.id}
                onClick={() => void reviewSession(selected.id, "approve")}
              >
                Approve
              </button>
              <button
                type="button"
                className="qs-btn qs-btn--danger qs-btn--sm"
                disabled={reviewBusy === selected.id}
                onClick={() => void reviewSession(selected.id, "reject")}
              >
                Reject
              </button>
            </div>
          </div>

          <AgentSessionEventLog events={events} loading={eventsLoading} />
          <AgentSessionInteractForm
            sessionId={selected.id}
            onInteractionAppended={(event) => {
              void mutateEvents((prev) => [event, ...(prev ?? [])], false);
            }}
          />
        </div>
      ) : null}

      <div className={isV4 ? "v4-routines-panel mt-6" : "mt-6 rounded-2xl border border-[color:var(--qs-border)] bg-black/30 p-4"}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-(--qs-text)">Routines</h3>
            <p className="mt-1 text-xs text-(--qs-text-3)">Recurring supervisor sessions via Celery schedule tick.</p>
          </div>
          {isV4 ? (
            <V4Badge tone="gold">{routines.filter((r) => r.is_active).length} active</V4Badge>
          ) : (
            <InfoHint
              title="Routines"
              description="Periodic Supervisor sessions triggered by schedule interval."
              options={["Create routine", "Trigger now", "Status monitoring"]}
            />
          )}
        </div>
        {!isV4 ? (
          <p className="mt-1 text-xs text-zinc-500">Recurring supervisor sessions via Celery schedule tick.</p>
        ) : null}
        <div className="mt-3 grid gap-2 md:grid-cols-[1fr_1fr_100px_auto]">
          <input className="qs-input" placeholder="Routine name" value={routineName} onChange={(e) => setRoutineName(e.target.value)} />
          <input className="qs-input" placeholder="Goal template" value={routineGoal} onChange={(e) => setRoutineGoal(e.target.value)} />
          <input
            className="qs-input"
            type="number"
            min={60}
            step={60}
            value={routineInterval}
            onChange={(e) => setRoutineInterval(Number(e.target.value || 3600))}
          />
          <button type="button" className="qs-btn qs-btn--primary qs-btn--sm gap-2" disabled={routineBusy} onClick={() => void createRoutine()}>
            <Plus className="h-4 w-4" aria-hidden />
            {routineBusy ? "Creating…" : "Create"}
          </button>
        </div>
        <div className="mt-3 space-y-2">
          {routines.map((routine) => (
            <div
              key={routine.id}
              className={
                isV4
                  ? "v4-session-row"
                  : "flex flex-wrap items-center justify-between gap-2 rounded-xl border border-zinc-800 bg-black/25 p-3"
              }
            >
              <p className="text-xs text-(--qs-text-2)">
                <span className="font-semibold text-(--qs-text)">{routine.name}</span> · every {routine.interval_seconds ?? 0}s · {routine.status}
              </p>
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void triggerRoutine(routine.id)}>
                Run now
              </button>
            </div>
          ))}
          {!routines.length ? <p className="text-xs text-(--qs-text-3)">No routines configured.</p> : null}
        </div>
      </div>

      {selected ? (
        <AgentSessionDetailDrawer
          session={selected}
          events={events}
          eventsLoading={eventsLoading}
          onClose={() => setSelectedSessionId(null)}
          onReview={async (decision) => {
            await reviewSession(selected.id, decision);
            await mutate();
          }}
          onInteractionAppended={(event) => {
            void mutateEvents((prev) => [event, ...(prev ?? [])], false);
          }}
        />
      ) : null}
    </Shell>
  );
}

