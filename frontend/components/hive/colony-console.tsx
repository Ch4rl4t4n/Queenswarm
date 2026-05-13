"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { QueenDashboardChrome } from "@/components/hive/queen-dashboard-chrome";
import { hiveFetch, hiveGet, hivePatchJson, hivePostJson, hivePutJson } from "@/lib/api";
import type { AgentRow, DashboardSummary, SystemStatusPayload, TaskRow } from "@/lib/hive-types";

interface ColonyConsoleProps {
  initialAgents: AgentRow[];
}

interface ConfigDraft {
  system_prompt: string;
  user_prompt_template: string | null;
  description: string;
  tagsStr: string;
  output_config: Record<string, unknown>;
  swarm_id: string | null;
  /** True → status offline + config is_active false. */
  inactive: boolean;
}

interface AgentConfigPayload {
  system_prompt: string;
  user_prompt_template: string | null;
  output_config: Record<string, unknown>;
  is_active?: boolean;
}

interface SwarmRowLite {
  id: string;
  name: string;
  purpose?: string;
  member_count?: number;
  local_memory?: Record<string, unknown> | null;
  is_active?: boolean;
}

/** UI-only label: orchestrator tier is always "Queen". */
function tierLabel(t: string): string {
  const u = t.toLowerCase();
  if (u === "orchestrator") return "Queen";
  if (u === "manager") return "Manager";
  if (u === "worker") return "Worker";
  return "Unassigned";
}

function descriptionFromOutputConfig(oc: Record<string, unknown>): string {
  const d = oc.description;
  return typeof d === "string" ? d : "";
}

function tagsStrFromOutputConfig(oc: Record<string, unknown>): string {
  const raw = oc.tags;
  if (Array.isArray(raw)) {
    return raw.map((x) => String(x)).join(", ");
  }
  if (typeof raw === "string") {
    return raw;
  }
  return "";
}

function swarmRowRole(sw: Pick<SwarmRowLite, "local_memory" | "purpose">): string {
  const lm = sw.local_memory ?? {};
  const hi = (lm.hive_ui as Record<string, unknown> | undefined) ?? {};
  const label = (hi.swarm_role_label as string) || (lm.swarm_role_label as string);
  if (label?.trim()) return label;
  return String(sw.purpose ?? "colony").replace(/_/g, " ");
}

function deriveInactive(agent: AgentRow, cfg?: AgentConfigPayload | null): boolean {
  if ((agent.status ?? "").toLowerCase() === "offline") {
    return true;
  }
  return cfg?.is_active === false;
}

export function ColonyConsole({ initialAgents }: ColonyConsoleProps) {
  const [agents, setAgents] = useState<AgentRow[]>(initialAgents);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [draftById, setDraftById] = useState<Record<string, ConfigDraft>>({});
  const [modalAgentId, setModalAgentId] = useState<string | null>(null);
  const [subSwarms, setSubSwarms] = useState<SwarmRowLite[]>([]);

  const [newName, setNewName] = useState("");
  const [newTier, setNewTier] = useState<"manager" | "worker">("worker");
  const [newPrompt, setNewPrompt] = useState("You are a Queenswarm specialist bee.");
  const [creating, setCreating] = useState(false);

  const [missionBrief, setMissionBrief] = useState("");
  const [missionBusy, setMissionBusy] = useState(false);
  const [missionErr, setMissionErr] = useState<string | null>(null);

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [costWindowUsd, setCostWindowUsd] = useState<number | null>(null);
  const [filterQuery, setFilterQuery] = useState("");
  const [systemPulse, setSystemPulse] = useState<SystemStatusPayload | null>(null);
  const [recentTasks, setRecentTasks] = useState<TaskRow[]>([]);
  const [telemetryBusy, setTelemetryBusy] = useState(true);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const res = await fetch("/api/proxy/dashboard/summary", { credentials: "include" });
        if (res.ok && alive) {
          setSummary((await res.json()) as DashboardSummary);
        }
      } catch {
        /* ignore */
      }
      try {
        const res = await fetch("/api/proxy/operator/costs/summary?days=30", { credentials: "include" });
        if (res.ok && alive) {
          const body = (await res.json()) as { series?: { spend_usd: number }[] };
          const total = (body.series ?? []).reduce((s, x) => s + (Number(x.spend_usd) || 0), 0);
          setCostWindowUsd(total);
        }
      } catch {
        /* ignore */
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function pollTelemetry(): Promise<void> {
      try {
        const [nextAgents, taskSlice, pulse] = await Promise.all([
          hiveFetch<AgentRow[]>("agents?limit=200"),
          hiveGet<TaskRow[]>("tasks?limit=10"),
          hiveGet<SystemStatusPayload>("system/status"),
        ]);
        if (cancelled) {
          return;
        }
        setAgents(nextAgents);
        setRecentTasks(taskSlice);
        setSystemPulse(pulse);
      } catch {
        /* keep last good snapshot */
      } finally {
        if (!cancelled) {
          setTelemetryBusy(false);
        }
      }
    }
    void pollTelemetry();
    const handle = window.setInterval(() => void pollTelemetry(), 8000);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, []);

  const filteredHoneycombAgents = useMemo(() => {
    const q = filterQuery.trim().toLowerCase();
    if (!q) {
      return agents;
    }
    return agents.filter((a) => {
      const name = a.name.toLowerCase();
      const tier = tierLabel(a.hive_tier ?? "").toLowerCase();
      const role = String(a.role ?? "").toLowerCase();
      return name.includes(q) || tier.includes(q) || role.includes(q);
    });
  }, [agents, filterQuery]);

  const grouped = useMemo(() => {
    const orchestrator: AgentRow[] = [];
    const managers: AgentRow[] = [];
    const workers: AgentRow[] = [];
    const unknown: AgentRow[] = [];
    for (const row of agents) {
      const tier = (row.hive_tier ?? "").toLowerCase();
      if (tier === "orchestrator") orchestrator.push(row);
      else if (tier === "manager") managers.push(row);
      else if (tier === "worker") workers.push(row);
      else unknown.push(row);
    }
    return { orchestrator, managers, workers, unknown };
  }, [agents]);

  const swarmLabelCount = useMemo(() => {
    const n = (grouped.managers.length > 0 ? 1 : 0) + (grouped.orchestrator.length > 0 ? 1 : 0);
    const swarms = new Set(agents.map((a) => a.swarm_id).filter(Boolean)).size;
    return Math.max(1, n + swarms);
  }, [agents, grouped]);

  const modalAgent = modalAgentId ? agents.find((a) => a.id === modalAgentId) : undefined;
  const modalDraft = modalAgentId ? draftById[modalAgentId] : undefined;
  const modalSwarmChosenId = modalDraft?.swarm_id?.trim() ?? "";
  const modalPromptOptional =
    modalDraft !== undefined && (modalDraft.inactive || modalSwarmChosenId === "");

  async function reloadAgents(): Promise<void> {
    try {
      const next = await hiveFetch<AgentRow[]>("agents?limit=200");
      setAgents(next);
    } catch {
      /* keep prior */
    }
  }

  useEffect(() => {
    void hiveGet<unknown>("swarms?limit=200")
      .then((d) => {
        const rows = Array.isArray(d)
          ? d
          : Array.isArray((d as { items?: unknown }).items)
            ? (d as { items: unknown[] }).items
            : Array.isArray((d as { swarms?: unknown }).swarms)
              ? (d as { swarms: unknown[] }).swarms
              : [];
        setSubSwarms(
          rows.filter(
            (r): r is SwarmRowLite =>
              typeof r === "object" &&
              r !== null &&
              "id" in r &&
              "name" in r &&
              typeof (r as SwarmRowLite).id === "string" &&
              typeof (r as SwarmRowLite).name === "string",
          ),
        );
      })
      .catch(() => {});
  }, []);

  async function runMission(): Promise<void> {
    if (!missionBrief.trim()) {
      window.alert("Enter a brief.");
      return;
    }
    setMissionErr(null);
    setMissionBusy(true);
    try {
      const cap = await hivePostJson<{ session_id?: string }>("ballroom/session", {});
      const sid = cap.session_id;
      if (!sid) {
        throw new Error("Missing session_id from ballroom.");
      }
      await hivePostJson("ballroom/mission", {
        user_brief: missionBrief.trim(),
        session_id: sid,
      });
      window.location.assign(`/ballroom?session=${encodeURIComponent(sid)}`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Mission failed";
      setMissionErr(msg);
      window.alert(msg);
    } finally {
      setMissionBusy(false);
    }
  }

  function isQueenAgent(agent: AgentRow): boolean {
    const tier = (agent.hive_tier ?? "").toLowerCase();
    return tier === "orchestrator" || agent.name.toLowerCase() === "orchestrator";
  }

  async function openConfigModal(agent: AgentRow): Promise<void> {
    if (isQueenAgent(agent)) {
      return;
    }
    setModalAgentId(agent.id);
    if (!agent.has_universal_config) {
      setDraftById((d) => ({
        ...d,
        [agent.id]: {
          system_prompt: "",
          user_prompt_template: null,
          description: "",
          tagsStr: "",
          output_config: agent.hive_tier ? { hive_tier: agent.hive_tier } : {},
          swarm_id: agent.swarm_id ?? null,
          inactive: deriveInactive(agent, null),
        },
      }));
      return;
    }
    try {
      const cfg = await hiveFetch<AgentConfigPayload>(`agents/${agent.id}/config`);
      const oc = { ...cfg.output_config };
      setDraftById((d) => ({
        ...d,
        [agent.id]: {
          system_prompt: cfg.system_prompt,
          user_prompt_template: cfg.user_prompt_template,
          description: descriptionFromOutputConfig(oc),
          tagsStr: tagsStrFromOutputConfig(oc),
          output_config: oc,
          swarm_id: agent.swarm_id ?? null,
          inactive: deriveInactive(agent, cfg),
        },
      }));
    } catch {
      setDraftById((d) => ({
        ...d,
        [agent.id]: {
          system_prompt: "",
          user_prompt_template: null,
          description: "",
          tagsStr: "",
          output_config: agent.hive_tier ? { hive_tier: agent.hive_tier } : {},
          swarm_id: agent.swarm_id ?? null,
          inactive: deriveInactive(agent, null),
        },
      }));
    }
  }

  function closeModal(): void {
    setModalAgentId(null);
  }

  async function saveModalConfig(): Promise<void> {
    if (!modalAgentId || !modalDraft) {
      return;
    }
    const swarmChosen = modalDraft.swarm_id?.trim() ?? "";
    const promptSkippable = modalDraft.inactive || !swarmChosen;
    if (!promptSkippable && !modalDraft.system_prompt.trim()) {
      window.alert("Prompt is required when the agent is active and has a swarm.");
      return;
    }
    setBusyId(modalAgentId);
    try {
      const tagList = modalDraft.tagsStr
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const oc: Record<string, unknown> = {
        ...modalDraft.output_config,
        description: modalDraft.description.trim(),
        tags: tagList,
      };
      await hivePutJson(`agents/${modalAgentId}/config`, {
        system_prompt: modalDraft.system_prompt.trim(),
        user_prompt_template: modalDraft.user_prompt_template ?? null,
        output_config: oc,
        is_active: !modalDraft.inactive,
      });

      const patchBody: {
        detach_from_swarm?: boolean;
        swarm_id?: string;
        status?: string;
      } = swarmChosen
        ? { detach_from_swarm: false, swarm_id: swarmChosen }
        : { detach_from_swarm: true };
      if (modalDraft.inactive) {
        patchBody.status = "offline";
      } else if (modalAgent && (modalAgent.status ?? "").toLowerCase() === "offline") {
        patchBody.status = "idle";
      }
      await hivePatchJson(`agents/${modalAgentId}`, patchBody);
      setDraftById((d) => {
        const next = { ...d };
        delete next[modalAgentId];
        return next;
      });
      closeModal();
      await reloadAgents();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusyId(null);
    }
  }

  async function createBee(): Promise<void> {
    if (!newName.trim()) {
      window.alert("Enter a name.");
      return;
    }
    setCreating(true);
    try {
      await hivePostJson("agents/dynamic", {
        name: newName.trim(),
        hive_tier: newTier,
        system_prompt: newPrompt.trim() || "You are a helpful AI agent.",
        user_prompt_template: null,
        tools: [],
        output_format: "text",
        output_destination: "dashboard",
        output_config: {},
        schedule_type: "on_demand",
        schedule_value: null,
      });
      setNewName("");
      await reloadAgents();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "Create failed");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-10 pb-24">
      <QueenDashboardChrome
        agents={filteredHoneycombAgents}
        summary={summary}
        costWindowUsd={costWindowUsd}
        filterQuery={filterQuery}
        onFilterChange={setFilterQuery}
        onHoneycombAgent={(a) => {
          if (isQueenAgent(a)) {
            return;
          }
          void openConfigModal(a);
        }}
        onAgentsReload={() => void reloadAgents()}
        swarmLabelCount={swarmLabelCount}
        systemStatus={systemPulse}
        recentTasks={recentTasks}
        telemetryLoading={telemetryBusy && !systemPulse}
      />

      {/* 1 — Queen mission */}
      <section id="hive-task" className="scroll-mt-28 mx-auto w-full max-w-3xl rounded-2xl border-[3px] border-pollen/35 bg-gradient-to-br from-[#14101a] to-[#08080f] p-6 shadow-[0_0_40px_rgb(255_184_0/0.12)] md:p-8">
        <h2 className="text-center font-[family-name:var(--font-poppins)] text-xl font-bold text-pollen md:text-left">
          Queen mission
        </h2>
        <p className="mt-2 text-center font-[family-name:var(--font-poppins)] text-sm text-zinc-400 md:text-left">
          After submit, the 7-step flow runs; Ballroom opens live transcript and voice.
        </p>
        <label className="mt-5 block qs-label">
          Brief
          <textarea
            value={missionBrief}
            onChange={(e) => setMissionBrief(e.target.value)}
            rows={6}
            className="mt-2 w-full rounded-xl border-[2px] border-cyan/25 bg-black/60 px-4 py-3 text-sm text-[#fafafa] outline-none focus:border-pollen/50"
            placeholder="What should the hive do?"
          />
        </label>
        <p className="mt-3 text-center font-[family-name:var(--font-poppins)] text-xs text-zinc-500 md:text-left">
          <Link href="/tasks/new" className="text-cyan/80 underline decoration-cyan/40 underline-offset-4 hover:text-pollen">
            Open full New task screen (step preview, recipe, submit)
          </Link>
        </p>
        {missionErr ? <p className="mt-2 text-sm text-danger">{missionErr}</p> : null}
        <button
          type="button"
          disabled={missionBusy}
          className="qs-btn qs-btn--primary qs-btn--xl qs-btn--full mt-6 disabled:opacity-45"
          onClick={() => void runMission()}
        >
          {missionBusy ? "Processing…" : "Run task"}
        </button>
      </section>

      {/* 2 — Agent creation */}
      <section id="hive-create" className="scroll-mt-28 mx-auto w-full max-w-3xl rounded-2xl border-[3px] border-cyan/30 bg-[#0a0a14]/95 p-6 shadow-[0_0_28px_rgb(0_255_255/0.08)] md:p-8">
        <h2 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#fafafa]">New manager / worker</h2>
        <p className="mt-2 font-[family-name:var(--font-poppins)] text-sm text-zinc-500">
          Add a bee to the hive. There is only one Queen. Use the swarm selector after spawn to tuck workers under managers;
          everyone appears together in{" "}
          <Link href="/#hive-live-swarm" className="font-semibold text-cyan/90 underline underline-offset-4 hover:text-pollen">
            Live network
          </Link>
          .
        </p>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <label className="block qs-label">
            Name
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="mt-2 w-full rounded-xl border-[2px] border-cyan/25 bg-black/55 px-3 py-2 text-sm text-[#fafafa] outline-none focus:border-pollen/45"
              placeholder="e.g. Research Manager"
            />
          </label>
          <label className="block qs-label">
            Tier
            <select
              value={newTier}
              onChange={(e) => setNewTier(e.target.value as "manager" | "worker")}
              className="mt-2 w-full rounded-xl border-[2px] border-cyan/25 bg-black/55 px-3 py-2 text-sm text-[#fafafa] outline-none focus:border-pollen/45"
            >
              <option value="manager">Manager</option>
              <option value="worker">Worker</option>
            </select>
          </label>
        </div>
        <label className="mt-4 block qs-label">
          Starting prompt
          <textarea
            value={newPrompt}
            onChange={(e) => setNewPrompt(e.target.value)}
            rows={3}
            className="mt-2 w-full rounded-xl border-[2px] border-cyan/25 bg-black/55 px-3 py-2 text-sm text-[#fafafa] outline-none focus:border-pollen/45"
          />
        </label>
        <button
          type="button"
          disabled={creating}
          className="mt-5 rounded-xl border-[3px] border-pollen/50 bg-pollen/15 px-6 py-3 font-semibold text-pollen disabled:opacity-40"
          onClick={() => void createBee()}
        >
          {creating ? "Adding…" : "Add agent"}
        </button>
      </section>

      <p className="text-center font-[family-name:var(--font-poppins)] text-sm text-zinc-400">
        Live room:{" "}
        <Link href="/ballroom" className="font-semibold text-data underline-offset-4 hover:text-pollen hover:underline">
          Ballroom
        </Link>
      </p>

      {modalAgent && modalDraft ? (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-4 sm:items-center"
          role="dialog"
          aria-modal="true"
          aria-labelledby="agent-config-title"
        >
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border-[3px] border-cyan/30 bg-[#0a0a14] p-6 shadow-[0_0_48px_rgb(0_255_255/0.12)]">
            <h3 id="agent-config-title" className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-pollen">
              {modalAgent.name}
            </h3>
            <p className="qs-meta-label mt-1 normal-case tracking-normal text-zinc-500">
              {tierLabel(modalAgent.hive_tier ?? "")}
            </p>

            <label className="mt-5 block qs-label">
              Manager / swarm
              <select
                value={modalDraft.swarm_id ?? ""}
                onChange={(ev) => {
                  const raw = ev.target.value;
                  setDraftById((d) => {
                    const cur = modalAgentId ? d[modalAgentId] : undefined;
                    if (!cur || !modalAgentId) return d;
                    return {
                      ...d,
                      [modalAgentId]: {
                        ...cur,
                        swarm_id: raw ? raw : null,
                      },
                    };
                  });
                }}
                className="mt-2 w-full rounded-xl border-[2px] border-cyan/25 bg-black/55 px-3 py-2 font-[family-name:var(--font-poppins)] text-sm text-[#fafafa] outline-none focus:border-pollen/50"
              >
                <option value="">— No swarm —</option>
                {subSwarms
                  .filter((s) => s.is_active !== false && !String(s.name).includes("__inactive_"))
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({swarmRowRole(s)})
                    </option>
                  ))}
              </select>
            </label>

            <label className="mt-4 flex cursor-pointer items-start gap-3 rounded-xl border-[2px] border-white/10 bg-black/35 px-3 py-3">
              <input
                type="checkbox"
                checked={modalDraft.inactive}
                className="mt-1 h-4 w-4 shrink-0 accent-pollen"
                aria-describedby="inactive-agent-hint"
                onChange={(ev) =>
                  setDraftById((d) => {
                    const cur = modalAgentId ? d[modalAgentId] : undefined;
                    if (!cur || !modalAgentId) return d;
                    return {
                      ...d,
                      [modalAgentId]: { ...cur, inactive: ev.target.checked },
                    };
                  })
                }
              />
              <span className="min-w-0">
                <span className="block font-[family-name:var(--font-poppins)] text-sm font-semibold text-zinc-200">
                  Inactive / offline
                </span>
                <span id="inactive-agent-hint" className="mt-1 block font-[family-name:var(--font-poppins)] text-xs leading-relaxed text-zinc-500">
                  Grid and list views stay muted. You can skip the prompt when offline or without a swarm.
                </span>
              </span>
            </label>

            <label className="mt-5 block qs-label">
              <span className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                Prompt
                {modalPromptOptional ? (
                  <span className="font-[family-name:var(--font-poppins)] text-[10px] font-normal normal-case tracking-normal text-zinc-600">
                    (optional — only needed for an active agent with a swarm)
                  </span>
                ) : null}
              </span>
              <textarea
                value={modalDraft.system_prompt}
                onChange={(ev) =>
                  setDraftById((d) => ({
                    ...d,
                    [modalAgentId!]: { ...modalDraft, system_prompt: ev.target.value },
                  }))
                }
                rows={5}
                className="mt-2 w-full rounded-xl border-[2px] border-cyan/25 bg-black/55 px-3 py-2 text-sm text-[#fafafa] outline-none focus:border-pollen/50"
              />
            </label>

            <label className="mt-4 block qs-label">
              Description
              <textarea
                value={modalDraft.description}
                onChange={(ev) =>
                  setDraftById((d) => ({
                    ...d,
                    [modalAgentId!]: { ...modalDraft, description: ev.target.value },
                  }))
                }
                rows={3}
                className="mt-2 w-full rounded-xl border-[2px] border-cyan/25 bg-black/55 px-3 py-2 text-sm text-[#fafafa] outline-none focus:border-pollen/50"
              />
            </label>

            <label className="mt-4 block qs-label">
              Tags (comma-separated)
              <input
                value={modalDraft.tagsStr}
                onChange={(ev) =>
                  setDraftById((d) => ({
                    ...d,
                    [modalAgentId!]: { ...modalDraft, tagsStr: ev.target.value },
                  }))
                }
                className="mt-2 w-full rounded-xl border-[2px] border-cyan/25 bg-black/55 px-3 py-2 text-sm text-[#fafafa] outline-none focus:border-pollen/50"
                placeholder="research, crypto, weekly"
              />
            </label>

            <div className="mt-6 flex flex-wrap justify-end gap-3">
              <button type="button" className="qs-btn qs-btn--ghost min-w-[9rem]" onClick={closeModal}>
                Close
              </button>
              <button
                type="button"
                disabled={busyId === modalAgentId}
                className="qs-btn qs-btn--primary min-w-[9rem] disabled:opacity-40"
                onClick={() => void saveModalConfig()}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
