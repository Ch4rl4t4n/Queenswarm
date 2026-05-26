"use client";

import type { JSX } from "react";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, Info, Play, Plus, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import { toast } from "sonner";

import { BrowserHarnessPanel } from "@/components/hive/browser-harness-panel";
import { AgentsPanelSkeleton } from "@/components/hive/agents-panel-skeleton";
import { AgentSessionReportDialog } from "@/components/hive/agent-session-report-dialog";
import { InfoHint } from "@/components/hive/info-hint";
import { VoiceSessionControls } from "@/components/hive/voice-session-controls";
import { usePlatform } from "@/components/hive/platform-context";
import { QsSelect } from "@/components/ui/qs-select";
import {
  V4Badge,
  V4Card,
  V4CardHeader,
  V4IconAgents,
  V4IconBolt,
  V4Stat,
} from "@/components/ui/v4";
import { HiveApiError, hiveDelete, hiveGet, hivePostJson } from "@/lib/api";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import { integrationsTabHref } from "@/lib/integrations-routes";
import { useRouteScopedPollOptions } from "@/lib/hooks/use-route-scoped-poll";
import type {
  SupervisorControlSummaryRow,
  SupervisorRoutineRow,
  SupervisorSessionRow,
} from "@/lib/hive-types";
import type { SoloSessionPreset, SoloSessionPresetsResponse } from "@/lib/solo-session-presets";
import { SOLO_PRESET_LANE_LABEL } from "@/lib/solo-session-presets";
import { runtimeModeLabel, sessionGoalPreview, sessionStatusTone, supervisorSessionBallroomHref, isActiveSupervisorSession } from "@/lib/supervisor-session";
import {
  playbookRecipeIdFromContext,
  playbookWasAutoSavedOnReview,
} from "@/lib/session-playbook-utils";

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
  const { soloMode } = usePlatform();
  const searchParams = useSearchParams();
  const [goal, setGoal] = useState("");
  const [runtimeMode, setRuntimeMode] = useState<"inprocess" | "durable">("inprocess");
  const [sessionRoles, setSessionRoles] = useState<string[]>([...ROLE_OPTIONS]);
  const [sessionSkills, setSessionSkills] = useState<string[]>(["context", "decide", "tdd"]);
  const [sessionRetrieval, setSessionRetrieval] = useState("customer_history+policy+last_3_tasks");
  const [activePresetId, setActivePresetId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reviewBusy, setReviewBusy] = useState<string | null>(null);
  const [routineName, setRoutineName] = useState("");
  const [routineGoal, setRoutineGoal] = useState("");
  const [routineInterval, setRoutineInterval] = useState(3600);
  const [routineBusy, setRoutineBusy] = useState(false);
  const [sessionQuery, setSessionQuery] = useState("");
  const [sessionStatusFilter, setSessionStatusFilter] = useState<SessionStatusFilter>("all");
  const [deleteBusy, setDeleteBusy] = useState<string | null>(null);
  const [clearAllBusy, setClearAllBusy] = useState(false);
  const [reportSessionId, setReportSessionId] = useState<string | null>(null);

  const sessionsPoll = useRouteScopedPollOptions(COCKPIT_POLL_BOARD_MS, "/agents");
  const routinesPoll = useRouteScopedPollOptions(COCKPIT_POLL_BOARD_MS * 1.5, "/agents");

  const {
    data: rawSessions = [],
    error,
    isLoading,
    mutate,
  } = useSWR<SupervisorSessionRow[]>(
    "hive/agent-sessions",
    () => hiveGet<SupervisorSessionRow[]>("agents/sessions?limit=40"),
    sessionsPoll,
  );
  const sessions = Array.isArray(rawSessions) ? rawSessions : [];

  const { data: rawRoutines = [], mutate: mutateRoutines } = useSWR<SupervisorRoutineRow[]>(
    "hive/agent-routines",
    () => hiveGet<SupervisorRoutineRow[]>("agents/routines?limit=40"),
    routinesPoll,
  );
  const routines = Array.isArray(rawRoutines) ? rawRoutines : [];
  const { data: summary, mutate: mutateSummary } = useSWR<SupervisorControlSummaryRow>(
    "hive/agent-sessions-summary",
    () => hiveGet<SupervisorControlSummaryRow>("agents/sessions/summary"),
    sessionsPoll,
  );

  const { data: soloPresets } = useSWR<SoloSessionPresetsResponse>(
    soloMode ? "hive/solo-session-presets" : null,
    () => hiveGet<SoloSessionPresetsResponse>("solo-operator/session-presets"),
    { revalidateOnFocus: false },
  );

  function applySessionPreset(preset: SoloSessionPreset): void {
    setGoal(preset.goal);
    setRuntimeMode(preset.runtime_mode);
    setSessionRoles(preset.roles.length > 0 ? preset.roles : [...ROLE_OPTIONS]);
    setSessionSkills(preset.skills.length > 0 ? preset.skills : ["context", "decide", "tdd"]);
    setSessionRetrieval(preset.retrieval_contract || "customer_history+policy+last_3_tasks");
    setActivePresetId(preset.id);
  }

  useEffect(() => {
    if (!soloMode || !soloPresets?.presets?.length) {
      return;
    }
    const presetParam = searchParams.get("preset")?.trim();
    if (!presetParam || activePresetId === presetParam) {
      return;
    }
    const match = soloPresets.presets.find((row) => row.id === presetParam);
    if (match) {
      applySessionPreset(match);
    }
  }, [soloMode, soloPresets, searchParams, activePresetId]);

  async function refreshSessionsAndSummary(): Promise<void> {
    await Promise.all([mutate(), mutateSummary()]);
  }

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

  async function createSession(): Promise<void> {
    const payload: CreateSessionPayload = {
      goal: goal.trim(),
      runtime_mode: runtimeMode,
      roles: sessionRoles.length > 0 ? sessionRoles : [...ROLE_OPTIONS],
      retrieval_contract: sessionRetrieval,
      skills: sessionSkills.length > 0 ? sessionSkills : ["context", "decide", "tdd"],
    };
    if (payload.goal.length < 4) {
      toast.error("Goal is too short.");
      return;
    }
    setBusy(true);
    try {
      await hivePostJson<SupervisorSessionRow>("agents/sessions", payload);
      setGoal("");
      setActivePresetId(null);
      setSessionRoles([...ROLE_OPTIONS]);
      setSessionSkills(["context", "decide", "tdd"]);
      setSessionRetrieval("customer_history+policy+last_3_tasks");
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
      const updated = await hivePostJson<{ context_summary?: Record<string, unknown> }>(
        `agents/sessions/${sessionId}/control`,
        { action },
      );
      await refreshSessionsAndSummary();
      const requeued = updated.context_summary?.requeued_sub_agents;
      if (action === "resume" && typeof requeued === "number" && requeued > 0) {
        toast.success(`Session resumed · ${requeued} sub-agent step(s) requeued`);
      } else {
        toast.success(`Session ${action} applied.`);
      }
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Control failed";
      toast.error(msg);
    }
  }

  async function deleteSession(sessionId: string): Promise<void> {
    setDeleteBusy(sessionId);
    try {
      await hiveDelete<{ deleted: boolean }>(`agents/sessions/${sessionId}`);
      await refreshSessionsAndSummary();
      toast.success("Session deleted.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Delete failed";
      toast.error(msg);
    } finally {
      setDeleteBusy(null);
    }
  }

  async function clearAllSessions(): Promise<void> {
    const targets = filteredSessions;
    if (targets.length === 0) {
      return;
    }
    const filterHint =
      sessionStatusFilter !== "all" || sessionQuery.trim()
        ? " z aktuálneho filtra"
        : "";
    const confirmed = window.confirm(
      `Vymazať ${targets.length} session${targets.length === 1 ? "" : "s"}${filterHint}? Táto akcia sa nedá vrátiť.`,
    );
    if (!confirmed) {
      return;
    }
    setClearAllBusy(true);
    try {
      const isFullList =
        sessionStatusFilter === "all" &&
        !sessionQuery.trim() &&
        targets.length === sessions.length;
      if (isFullList) {
        const result = await hiveDelete<{ deleted_count: number }>("agents/sessions");
        await refreshSessionsAndSummary();
        toast.success(`Vymazaných ${result.deleted_count} sessions.`);
        return;
      }
      let deletedCount = 0;
      for (const session of targets) {
        try {
          await hiveDelete<{ deleted: boolean }>(`agents/sessions/${session.id}`);
          deletedCount += 1;
        } catch (e) {
          const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Delete failed";
          toast.error(`${shortSessionId(session.id)}: ${msg}`);
        }
      }
      await refreshSessionsAndSummary();
      if (deletedCount > 0) {
        toast.success(`Vymazaných ${deletedCount} sessions.`);
      }
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Clear all failed";
      toast.error(msg);
    } finally {
      setClearAllBusy(false);
    }
  }

  async function reviewSession(
    sessionId: string,
    decision: "approve" | "reject",
    priorPlaybookRecipeId: string | null = null,
  ): Promise<void> {
    setReviewBusy(sessionId);
    try {
      const updated = await hivePostJson<{ context_summary?: Record<string, unknown> }>(
        `agents/sessions/${sessionId}/review`,
        { decision },
      );
      await mutate();
      const requeued = updated.context_summary?.requeued_sub_agents;
      const resumed = updated.context_summary?.resumed_sub_agents;
      const autoSavedPlaybook = playbookWasAutoSavedOnReview(updated.context_summary, priorPlaybookRecipeId);
      if (autoSavedPlaybook) {
        toast.success(
          <span>
            Session approved · operator playbook auto-saved.{" "}
            <Link href="/recipes" className="text-pollen underline">
              Open recipes
            </Link>
          </span>,
        );
      } else if (decision === "approve" && typeof requeued === "number" && requeued > 0) {
        toast.success(`Session approved · ${requeued} durable step(s) requeued`);
      } else if (decision === "approve" && typeof resumed === "number" && resumed > 0) {
        toast.success(`Session approved · ${resumed} in-process step(s) resumed`);
      } else {
        toast.success(`Session ${decision}d.`);
      }
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
      <V4Card id="sessions" className="scroll-mt-28">
        <V4CardHeader
          title="Dynamic supervisor sessions"
          description="Spawn sub-agents, track statuses, and interact through shared memory logs."
        />
        <div
          role="alert"
          data-testid="agents-sessions-error"
          className="rounded-xl border border-(--qs-red)/40 bg-(--qs-red)/10 px-4 py-4"
        >
          <p className="text-sm text-(--qs-text)">
            Session panel unavailable: <span className="text-(--qs-red)">{error.message}</span>
          </p>
          <p className="mt-2 text-xs text-(--qs-text-3)">
            Verify supervisor feature flags (`SUPERVISOR_DYNAMIC_SUBAGENTS_ENABLED`, `LIGHT_CONTROL_PLANE_ENABLED`) and
            API health, then retry.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5" onClick={() => void mutate()}>
              <RefreshCw className="h-3.5 w-3.5" aria-hidden />
              Retry
            </button>
            <Link href={integrationsTabHref("active", "ecosystem")} className="qs-btn qs-btn--ghost qs-btn--sm">
              Open Tool Hub
            </Link>
          </div>
        </div>
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
            <Link href={integrationsTabHref("active", "ecosystem")} className="qs-btn qs-btn--ghost qs-btn--sm">
              Tool hub
            </Link>
          }
        />
      ) : (
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold leading-snug text-zinc-100">Dynamic Supervisor Sessions</h2>
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
            <Link href={integrationsTabHref("active", "ecosystem")} className="qs-btn qs-btn--ghost qs-btn--sm">
              Tool Hub
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

      {soloMode && soloPresets?.presets?.length ? (
        <div className={isV4 ? "mt-4" : "mt-3"}>
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-(--qs-text-3)">
            Solo quick-start
          </p>
          <div className="flex flex-wrap gap-2">
            {soloPresets.presets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className={
                  activePresetId === preset.id
                    ? "qs-btn qs-btn--primary qs-btn--sm"
                    : "qs-btn qs-btn--ghost qs-btn--sm"
                }
                onClick={() => applySessionPreset(preset)}
              >
                {SOLO_PRESET_LANE_LABEL[preset.lane] ?? preset.lane}: {preset.label.split("—").pop()?.trim() ?? preset.label}
              </button>
            ))}
          </div>
        </div>
      ) : null}

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

      <div className={isV4 ? "mt-5 flex flex-col gap-3 md:flex-row md:items-stretch" : "mt-4 grid gap-2 rounded-2xl border border-zinc-800 bg-black/20 p-3 md:grid-cols-[1fr_180px]"}>
        <input
          className="qs-input w-full min-w-0 flex-1"
          placeholder="Filter sessions by goal / status / runtime…"
          value={sessionQuery}
          onChange={(event) => setSessionQuery(event.target.value)}
        />
        <QsSelect
          className="w-full min-w-0 md:w-40 md:shrink-0"
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

      <div className="mt-4">
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--qs-text-3)">
            Sessions
            {!isLoading && filteredSessions.length > 0 ? (
              <span className="ml-2 font-normal normal-case tracking-normal text-(--qs-text-4)">
                ({filteredSessions.length})
              </span>
            ) : null}
          </p>
          {!isLoading && filteredSessions.length > 5 ? (
            <span className="text-[10px] text-(--qs-text-4)">Scroll for older</span>
          ) : null}
        </div>
        <div className="v4-sessions-list-scroll hive-scrollbar">
        {isLoading ? (
          <AgentsPanelSkeleton rows={3} />
        ) : filteredSessions.length === 0 ? (
          <div
            className="rounded-xl border border-dashed border-(--qs-border) bg-black/20 px-4 py-6 text-center"
            data-testid="agents-sessions-empty"
          >
            <p className="text-sm text-(--qs-text-2)">
              {sessions.length === 0
                ? "No supervisor sessions yet."
                : "No sessions match this filter."}
            </p>
            <p className="mt-1 text-xs text-(--qs-text-3)">
              {sessions.length === 0
                ? "Describe a goal above and spawn your first dynamic session."
                : "Clear the filter or pick another status."}
            </p>
            {sessions.length === 0 ? (
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm mt-4 gap-1.5"
                onClick={() => {
                  const input = document.querySelector<HTMLInputElement>(
                    'input[placeholder="Session goal — e.g. investigate onboarding drop-off…"]',
                  );
                  input?.focus();
                }}
              >
                <Plus className="h-3.5 w-3.5" aria-hidden />
                Create first session
              </button>
            ) : (
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm mt-4"
                onClick={() => {
                  setSessionQuery("");
                  setSessionStatusFilter("all");
                }}
              >
                Reset filters
              </button>
            )}
          </div>
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
                    {playbookRecipeIdFromContext(session.context_summary) ? (
                      <Link href="/recipes">
                        <V4Badge tone="gold">playbook</V4Badge>
                      </Link>
                    ) : null}
                  </div>
                  <p className="v4-session-goal text-sm font-medium text-(--qs-text)" title={session.goal}>
                    {sessionGoalPreview(session.goal)}
                  </p>
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  <span className="text-xs text-(--qs-text-3)">
                    {sessionRuntimeLabel(session)} · {(session.sub_agents ?? []).length} agents
                  </span>
                  <Link href={supervisorSessionBallroomHref(session.id)} className="qs-btn qs-btn--ghost qs-btn--sm">
                    Ballroom
                  </Link>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
                    aria-label={`Session report ${shortSessionId(session.id)}`}
                    onClick={() => setReportSessionId(session.id)}
                  >
                    <Info className="h-3.5 w-3.5" aria-hidden />
                    Info
                  </button>
                  {isActiveSupervisorSession(session.status) ? (
                    <>
                      <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void controlSession(session.id, "pause")}>
                        Pause
                      </button>
                      <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void controlSession(session.id, "resume")}>
                        Resume
                      </button>
                      <button type="button" className="qs-btn qs-btn--danger qs-btn--sm" onClick={() => void controlSession(session.id, "stop")}>
                        Stop
                      </button>
                    </>
                  ) : null}
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm text-(--qs-red)"
                    disabled={deleteBusy === session.id}
                    onClick={() => void deleteSession(session.id)}
                  >
                    {deleteBusy === session.id ? "Deleting…" : "Delete"}
                  </button>
                  {session.status === "needs_input" ? (
                    <>
                      <button
                        type="button"
                        className="qs-btn qs-btn--green qs-btn--sm"
                        disabled={reviewBusy === session.id}
                        onClick={() =>
                          void reviewSession(
                            session.id,
                            "approve",
                            playbookRecipeIdFromContext(session.context_summary),
                          )
                        }
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className="qs-btn qs-btn--danger qs-btn--sm"
                        disabled={reviewBusy === session.id}
                        onClick={() =>
                          void reviewSession(session.id, "reject", playbookRecipeIdFromContext(session.context_summary))
                        }
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
                    <p className="v4-session-goal truncate text-sm font-semibold text-zinc-100" title={session.goal}>
                      {sessionGoalPreview(session.goal)}
                    </p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {runtimeModeLabel(session.runtime_mode)} · {session.status} · {(session.sub_agents ?? []).length} sub-agents
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <span className={`qs-pill qs-pill--active-${sessionStatusTone(session.status)}`}>{session.status}</span>
                    {session.status === "needs_input" ? (
                      <span className="rounded-full border border-[#FFB800]/40 bg-[#FFB800]/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.08em] text-[#FFB800]">
                        needs input
                      </span>
                    ) : null}
                    <Link href={supervisorSessionBallroomHref(session.id)} className="qs-btn qs-btn--ghost qs-btn--sm">
                      Ballroom
                    </Link>
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
                      aria-label={`Session report ${shortSessionId(session.id)}`}
                      onClick={() => setReportSessionId(session.id)}
                    >
                      <Info className="h-3.5 w-3.5" aria-hidden />
                      Info
                    </button>
                    {isActiveSupervisorSession(session.status) ? (
                      <>
                        <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void controlSession(session.id, "pause")}>
                          Pause
                        </button>
                        <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void controlSession(session.id, "resume")}>
                          Resume
                        </button>
                        <button type="button" className="qs-btn qs-btn--danger qs-btn--sm" onClick={() => void controlSession(session.id, "stop")}>
                          Stop
                        </button>
                      </>
                    ) : null}
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm text-(--qs-red)"
                      disabled={deleteBusy === session.id}
                      onClick={() => void deleteSession(session.id)}
                    >
                      {deleteBusy === session.id ? "Deleting…" : "Delete"}
                    </button>
                    <button
                      type="button"
                      className="qs-btn qs-btn--green qs-btn--sm"
                      disabled={reviewBusy === session.id}
                      onClick={() =>
                        void reviewSession(
                          session.id,
                          "approve",
                          playbookRecipeIdFromContext(session.context_summary),
                        )
                      }
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="qs-btn qs-btn--danger qs-btn--sm"
                      disabled={reviewBusy === session.id}
                      onClick={() =>
                        void reviewSession(session.id, "reject", playbookRecipeIdFromContext(session.context_summary))
                      }
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
        {filteredSessions.length > 0 ? (
          <button
            type="button"
            className="qs-btn qs-btn--danger mt-3 w-full justify-center py-2.5 text-sm font-semibold disabled:opacity-45"
            disabled={clearAllBusy || isLoading}
            onClick={() => void clearAllSessions()}
          >
            {clearAllBusy
              ? "Clearing…"
              : sessionStatusFilter !== "all" || sessionQuery.trim()
                ? `Clear filtered (${filteredSessions.length})`
                : `Clear all (${filteredSessions.length})`}
          </button>
        ) : null}
      </div>

      <AgentSessionReportDialog
        sessionId={reportSessionId}
        open={reportSessionId !== null}
        onOpenChange={(open) => {
          if (!open) {
            setReportSessionId(null);
          }
        }}
      />

      <div className={isV4 ? "v4-routines-panel mt-6" : "mt-6 rounded-2xl border border-[color:var(--qs-border)] bg-black/30 p-4"}>
        {isV4 ? (
          <div className="v4-routines-panel__head">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-(--qs-text)">Routines</h3>
              <V4Badge tone="gold" className="shrink-0">
                {routines.filter((r) => r.is_active).length} active
              </V4Badge>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-(--qs-text-3)">
              Recurring supervisor sessions via Celery schedule tick.
            </p>
          </div>
        ) : (
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-(--qs-text)">Routines</h3>
              <p className="mt-1 text-xs text-(--qs-text-3)">Recurring supervisor sessions via Celery schedule tick.</p>
            </div>
            <InfoHint
              title="Routines"
              description="Periodic Supervisor sessions triggered by schedule interval."
              options={["Create routine", "Trigger now", "Status monitoring"]}
            />
          </div>
        )}
        {!isV4 ? (
          <p className="mt-1 text-xs text-zinc-500">Recurring supervisor sessions via Celery schedule tick.</p>
        ) : null}
        <div className={isV4 ? "v4-routines-form mt-4" : "mt-3 grid gap-2 md:grid-cols-[1fr_1fr_100px_auto]"}>
          <input className="qs-input w-full min-w-0" placeholder="Routine name" value={routineName} onChange={(e) => setRoutineName(e.target.value)} />
          <input className="qs-input w-full min-w-0" placeholder="Goal template" value={routineGoal} onChange={(e) => setRoutineGoal(e.target.value)} />
          <input
            className="qs-input w-full min-w-0"
            type="number"
            min={60}
            step={60}
            value={routineInterval}
            onChange={(e) => setRoutineInterval(Number(e.target.value || 3600))}
          />
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm w-full justify-center gap-2 md:w-auto"
            disabled={routineBusy}
            onClick={() => void createRoutine()}
          >
            <Plus className="h-4 w-4 shrink-0" aria-hidden />
            {routineBusy ? "Creating…" : "Create"}
          </button>
        </div>
        <div className="v4-routines-list-scroll hive-scrollbar mt-3">
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
    </Shell>
  );
}

