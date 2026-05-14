"use client";

import type { JSX } from "react";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { toast } from "sonner";

import { AgentSessionDetailDrawer } from "@/components/hive/agent-session-detail-drawer";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { SupervisorSessionEventRow, SupervisorSessionRow } from "@/lib/hive-types";
import { runtimeModeLabel } from "@/lib/supervisor-session";

interface CreateSessionPayload {
  goal: string;
  runtime_mode: "inprocess" | "durable";
  roles: string[];
}

const ROLE_OPTIONS = ["researcher", "coder", "browser_operator", "critic", "designer"] as const;

export function AgentsSessionsPanel(): JSX.Element {
  const [goal, setGoal] = useState("");
  const [runtimeMode, setRuntimeMode] = useState<"inprocess" | "durable">("inprocess");
  const [busy, setBusy] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

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

  const selected = useMemo(
    () => sessions.find((session) => session.id === selectedSessionId) ?? null,
    [sessions, selectedSessionId],
  );

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

  if (error) {
    return (
      <section className="rounded-2xl border border-danger/30 bg-danger/5 p-4">
        <p className="text-sm text-danger">
          Session panel unavailable ({error.message}). Enable dynamic supervisor feature flags first.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-3xl qs-rim-cyan-soft bg-[#0a0f18]/80 p-5 md:p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">Dynamic Supervisor Sessions</h2>
          <p className="mt-1 text-xs text-zinc-400">
            Spawn sub-agents, track statuses, and interact through shared memory logs.
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 rounded-2xl border border-cyan/20 bg-black/30 p-4 md:grid-cols-[1fr_auto_auto]">
        <input
          className="qs-input"
          placeholder="Session goal (e.g. Investigate onboarding drop-off and propose implementation)"
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
        />
        <select
          className="qs-input"
          value={runtimeMode}
          onChange={(event) => setRuntimeMode(event.target.value as "inprocess" | "durable")}
        >
          <option value="inprocess">in-process</option>
          <option value="durable">durable</option>
        </select>
        <button
          type="button"
          className="qs-btn qs-btn--primary qs-btn--sm disabled:opacity-40"
          disabled={busy}
          onClick={() => void createSession()}
        >
          {busy ? "Creating..." : "Create session"}
        </button>
      </div>

      <div className="mt-4 grid gap-3">
        {isLoading ? (
          <p className="text-sm text-zinc-500">Loading sessions...</p>
        ) : sessions.length === 0 ? (
          <p className="text-sm text-zinc-500">No sessions yet.</p>
        ) : (
          sessions.map((session) => (
            <div key={session.id} className="rounded-2xl border border-zinc-800 bg-black/25 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-zinc-100">{session.goal}</p>
                  <p className="mt-1 text-xs text-zinc-500">
                    {runtimeModeLabel(session.runtime_mode)} · {session.status} · {session.sub_agents.length} sub-agents
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    onClick={() => setSelectedSessionId(session.id)}
                  >
                    Open
                  </button>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    onClick={() => void controlSession(session.id, "pause")}
                  >
                    Pause
                  </button>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    onClick={() => void controlSession(session.id, "resume")}
                  >
                    Resume
                  </button>
                  <button
                    type="button"
                    className="qs-btn qs-btn--danger qs-btn--sm"
                    onClick={() => void controlSession(session.id, "stop")}
                  >
                    Stop
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {selected ? (
        <AgentSessionDetailDrawer
          session={selected}
          events={events}
          eventsLoading={eventsLoading}
          onClose={() => setSelectedSessionId(null)}
          onInteractionAppended={(event) => {
            void mutateEvents((prev) => [event, ...(prev ?? [])], false);
          }}
        />
      ) : null}
    </section>
  );
}

