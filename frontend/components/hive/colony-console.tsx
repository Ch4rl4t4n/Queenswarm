"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { HexAgentCard } from "@/components/hive/hex-agent-card";
import { QueenDashboardChrome } from "@/components/hive/queen-dashboard-chrome";
import { hiveDelete, hiveFetch, hiveGet, hivePatchJson, hivePostJson, hivePutJson } from "@/lib/api";
import type { AgentRow, DashboardSummary, SystemStatusPayload, TaskRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

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
}

interface AgentConfigPayload {
  system_prompt: string;
  user_prompt_template: string | null;
  output_config: Record<string, unknown>;
}

interface SwarmRowLite {
  id: string;
  name: string;
  purpose?: string;
  member_count?: number;
  local_memory?: Record<string, unknown> | null;
  is_active?: boolean;
}

/** UI-only label: orchestrator tier is always „Queen“. */
function tierLabel(t: string): string {
  const u = t.toLowerCase();
  if (u === "orchestrator") return "Queen";
  if (u === "manager") return "Manažér";
  if (u === "worker") return "Robotník";
  return "Nezaradené";
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

  const hierarchy = useMemo(() => {
    const { orchestrator, managers, workers, unknown } = grouped;
    const pool = [...workers, ...unknown];
    const teamByManager = new Map<string, AgentRow[]>();
    for (const m of managers) {
      teamByManager.set(m.id, []);
    }
    const ungrouped: AgentRow[] = [];
    for (const w of pool) {
      const sid = w.swarm_id;
      let assigned = false;
      if (sid) {
        for (const m of managers) {
          if (m.swarm_id && m.swarm_id === sid) {
            teamByManager.get(m.id)!.push(w);
            assigned = true;
            break;
          }
        }
      }
      if (!assigned) {
        ungrouped.push(w);
      }
    }
    return {
      queen: orchestrator[0] ?? null,
      managers,
      teamByManager,
      ungrouped,
    };
  }, [grouped]);

  const modalAgent = modalAgentId ? agents.find((a) => a.id === modalAgentId) : undefined;
  const modalDraft = modalAgentId ? draftById[modalAgentId] : undefined;

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
      window.alert("Zadaj zadanie.");
      return;
    }
    setMissionErr(null);
    setMissionBusy(true);
    try {
      const cap = await hivePostJson<{ session_id?: string }>("ballroom/session", {});
      const sid = cap.session_id;
      if (!sid) {
        throw new Error("Chýba session_id z ballroom.");
      }
      await hivePostJson("ballroom/mission", {
        user_brief: missionBrief.trim(),
        session_id: sid,
      });
      window.location.assign(`/ballroom?session=${encodeURIComponent(sid)}`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Misia zlyhala";
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
    if (!modalDraft.system_prompt.trim()) {
      window.alert("Prompt je povinný.");
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
        system_prompt: modalDraft.system_prompt,
        user_prompt_template: modalDraft.user_prompt_template ?? null,
        output_config: oc,
      });
      const swarmPick = modalDraft.swarm_id?.trim();
      if (swarmPick) {
        await hivePatchJson(`agents/${modalAgentId}`, {
          detach_from_swarm: false,
          swarm_id: swarmPick,
        });
      } else {
        await hivePatchJson(`agents/${modalAgentId}`, {
          detach_from_swarm: true,
        });
      }
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

  async function removeBee(agent: AgentRow): Promise<void> {
    if (isQueenAgent(agent)) {
      window.alert("Queen je fixná.");
      return;
    }
    if (!window.confirm(`Odstrániť ${agent.name}?`)) {
      return;
    }
    setBusyId(agent.id);
    try {
      await hiveDelete(`agents/${agent.id}`);
      await reloadAgents();
      if (modalAgentId === agent.id) {
        closeModal();
      }
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setBusyId(null);
    }
  }

  async function createBee(): Promise<void> {
    if (!newName.trim()) {
      window.alert("Zadaj meno.");
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

      {/* 1 — Úloha */}
      <section id="hive-task" className="scroll-mt-28 mx-auto w-full max-w-3xl rounded-2xl border-[3px] border-pollen/35 bg-gradient-to-br from-[#14101a] to-[#08080f] p-6 shadow-[0_0_40px_rgb(255_184_0/0.12)] md:p-8">
        <h2 className="text-center font-[family-name:var(--font-poppins)] text-xl font-bold text-pollen md:text-left">
          Úloha pre Queen
        </h2>
        <p className="mt-2 text-center font-[family-name:var(--font-inter)] text-sm text-zinc-400 md:text-left">
          Po odoslaní beží 7-krokový tok; Ballroom otvorí live prepis a hlas.
        </p>
        <label className="mt-5 block text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
          Zadanie
          <textarea
            value={missionBrief}
            onChange={(e) => setMissionBrief(e.target.value)}
            rows={6}
            className="mt-2 w-full rounded-xl border-[2px] border-cyan/25 bg-black/60 px-4 py-3 text-sm text-[#fafafa] outline-none focus:border-pollen/50"
            placeholder="Čo má úľ urobiť?"
          />
        </label>
        <p className="mt-3 text-center font-[family-name:var(--font-inter)] text-xs text-zinc-500 md:text-left">
          <Link href="/tasks/new" className="text-cyan/80 underline decoration-cyan/40 underline-offset-4 hover:text-pollen">
            Otvoriť celú obrazovku Nový task (náhľad krokov, recept, odoslanie)
          </Link>
        </p>
        {missionErr ? <p className="mt-2 text-sm text-danger">{missionErr}</p> : null}
        <button
          type="button"
          disabled={missionBusy}
          className="qs-btn qs-btn--primary qs-btn--xl qs-btn--full mt-6 disabled:opacity-45"
          onClick={() => void runMission()}
        >
          {missionBusy ? "Spracúvam…" : "Spusti úlohu"}
        </button>
      </section>

      {/* 2 — Tvorba agentov (pod úlohou) */}
      <section id="hive-create" className="scroll-mt-28 mx-auto w-full max-w-3xl rounded-2xl border-[3px] border-cyan/30 bg-[#0a0a14]/95 p-6 shadow-[0_0_28px_rgb(0_255_255/0.08)] md:p-8">
        <h2 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#fafafa]">Nový manažér / robotník</h2>
        <p className="mt-2 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
          Pridaj včelu do úľa. Queen ostáva jedna; robotníci pod manažérom sa zobrazia v stromčeku, ak majú rovnaké{" "}
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-cyan/70">swarm_id</span> ako manažér.
        </p>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <label className="block text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
            Meno
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="mt-2 w-full rounded-xl border-[2px] border-cyan/25 bg-black/55 px-3 py-2 text-sm text-[#fafafa] outline-none focus:border-pollen/45"
              placeholder="Napr. Research Manager"
            />
          </label>
          <label className="block text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
            Úroveň
            <select
              value={newTier}
              onChange={(e) => setNewTier(e.target.value as "manager" | "worker")}
              className="mt-2 w-full rounded-xl border-[2px] border-cyan/25 bg-black/55 px-3 py-2 text-sm text-[#fafafa] outline-none focus:border-pollen/45"
            >
              <option value="manager">Manažér</option>
              <option value="worker">Robotník</option>
            </select>
          </label>
        </div>
        <label className="mt-4 block text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
          Začiatočný prompt
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
          className="mt-5 rounded-xl border-[3px] border-pollen/50 bg-pollen/15 px-5 py-3 font-semibold text-pollen disabled:opacity-40"
          onClick={() => void createBee()}
        >
          {creating ? "Pridávam…" : "Pridať agenta"}
        </button>
      </section>

      {/* 3 — Hierarchia Queen → manažéri → tímy (rovnaké hex dlaždice ako Živá sieť / Hierarchia) */}
      <section id="hive-hierarchy" className="scroll-mt-28 relative w-full overflow-x-auto rounded-3xl qs-rim bg-[#06060c]/90 px-4 py-8 md:px-8 md:py-10">
        <h2 className="mb-2 text-center font-[family-name:var(--font-poppins)] text-xs font-bold uppercase tracking-[0.28em] text-pollen/90">
          Hierarchia úľa
        </h2>
        <p className="mx-auto mb-10 max-w-2xl text-center font-[family-name:var(--font-inter)] text-sm text-zinc-500">
          Queen riadi manažérov · rovnaké SVG hex dlaždice ako v zozname agentov vyššie; swarm farba rámu podľa lane.
        </p>

        {hierarchy.queen ? (
          <div className="flex flex-col items-center">
            <HexAgentCard agent={hierarchy.queen} isQueen renderAsDiv />
            <p className="mt-3 max-w-[260px] text-center text-[11px] leading-relaxed text-zinc-500">
              Fixná hlava úľa — bez úprav konfigurácie.
            </p>

            {/* Konektor: z Queen do hornej čiary */}
            <div className="flex flex-col items-center" aria-hidden>
              <div className="h-10 w-[4px] rounded-full bg-gradient-to-b from-pollen via-pollen/60 to-cyan/50" />
              <div
                className={cn(
                  "h-[4px] w-[min(92vw,56rem)] max-w-full rounded-full bg-gradient-to-r from-transparent via-cyan/45 to-transparent",
                  hierarchy.managers.length === 0 && "opacity-40",
                )}
              />
            </div>

            {hierarchy.managers.length === 0 ? (
              <p className="mt-6 text-center text-sm text-zinc-500">Žiadni manažéri — pridaj manažéra vyššie v formulári.</p>
            ) : (
              <div className="mt-0 grid w-full max-w-6xl grid-cols-1 gap-10 md:grid-cols-2 xl:grid-cols-3">
                {hierarchy.managers.map((mgr, mi) => {
                  const team = hierarchy.teamByManager.get(mgr.id) ?? [];
                  const lineClass =
                    mi % 3 === 0
                      ? "from-cyan/70 to-cyan/20"
                      : mi % 3 === 1
                        ? "from-emerald-400/70 to-emerald-400/15"
                        : "from-sky-400/70 to-sky-400/15";
                  return (
                    <div key={mgr.id} className="flex flex-col items-center">
                      <div
                        className={cn("mb-2 h-8 w-[4px] rounded-full bg-gradient-to-b", lineClass)}
                        aria-hidden
                      />
                      <HexAgentCard agent={mgr} onClick={() => void openConfigModal(mgr)} />
                      <p className="mt-2 max-w-[180px] text-center text-[11px] text-zinc-500">Klikni pre prompt, popis a tagy.</p>
                      <button
                        type="button"
                        disabled={busyId === mgr.id}
                        className="qs-btn qs-btn--danger qs-btn--sm mt-3"
                        onClick={() => void removeBee(mgr)}
                      >
                        Zmazať
                      </button>

                      <div className={cn("my-4 h-6 w-[4px] rounded-full bg-gradient-to-b", lineClass)} aria-hidden />

                      <p className="mb-3 font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.2em] text-alert/80">
                        Tím ({team.length})
                      </p>
                      {team.length === 0 ? (
                        <p className="max-w-[14rem] text-center text-[11px] text-zinc-600">
                          Rovnaký swarm_id ako tento manažér pripojí robotníkov sem.
                        </p>
                      ) : (
                        <div className="flex w-full flex-col items-center gap-4">
                          {team.map((w) => (
                            <div key={w.id} className="flex flex-col items-center gap-1">
                              <HexAgentCard agent={w} onClick={() => void openConfigModal(w)} />
                              <button
                                type="button"
                                disabled={busyId === w.id}
                                className="qs-btn qs-btn--danger qs-btn--sm mt-3"
                                onClick={() => void removeBee(w)}
                              >
                                Zmazať
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ) : (
          <p className="text-center text-sm text-alert">Chýba Queen (orchestrator) v registri agentov.</p>
        )}

        {hierarchy.ungrouped.length > 0 ? (
          <div className="mx-auto mt-12 max-w-5xl border-t border-white/10 pt-8">
            <h3 className="mb-4 text-center font-[family-name:var(--font-poppins)] text-sm font-semibold text-zinc-300">
              Robotníci mimo tímov <span className="text-zinc-500">({hierarchy.ungrouped.length})</span>
            </h3>
            <p className="mx-auto mb-6 max-w-xl text-center text-xs text-zinc-600">
              Priraď ich k manažérovi zdieľaným <span className="text-cyan/70">swarm_id</span> (napr. v API alebo DB), potom sa zobrazia pod príslušným stĺpcom.
            </p>
            <div className="flex flex-wrap justify-center gap-6">
              {hierarchy.ungrouped.map((a) => (
                <div key={a.id} className="flex flex-col items-center gap-1">
                  <HexAgentCard agent={a} onClick={() => void openConfigModal(a)} />
                  <button
                    type="button"
                    disabled={busyId === a.id}
                    className="qs-btn qs-btn--danger qs-btn--sm mt-3"
                    onClick={() => void removeBee(a)}
                  >
                    Zmazať
                  </button>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>

      <p className="text-center font-[family-name:var(--font-inter)] text-sm text-zinc-400">
        Live miestnosť:{" "}
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
            <p className="mt-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] uppercase text-zinc-500">
              {tierLabel(modalAgent.hive_tier ?? "")}
            </p>

            <label className="mt-5 block text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
              Manažér / swarm
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
                className="mt-2 w-full rounded-xl border-[2px] border-cyan/25 bg-black/55 px-3 py-2 font-[family-name:var(--font-jetbrains-mono)] text-sm text-[#fafafa] outline-none focus:border-pollen/50"
              >
                <option value="">— Bez swarmu —</option>
                {subSwarms
                  .filter((s) => s.is_active !== false && !String(s.name).includes("__inactive_"))
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({swarmRowRole(s)})
                    </option>
                  ))}
              </select>
            </label>

            <label className="mt-5 block text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
              Prompt
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

            <label className="mt-4 block text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
              Popis
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

            <label className="mt-4 block text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
              Tagy (čiarkou oddelené)
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

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="button"
                disabled={busyId === modalAgentId}
                className="flex-1 rounded-xl border-[3px] border-pollen/50 bg-pollen/20 py-2.5 text-sm font-semibold text-pollen disabled:opacity-40"
                onClick={() => void saveModalConfig()}
              >
                Uložiť
              </button>
              <button
                type="button"
                className="rounded-xl border-[2px] border-zinc-600 px-4 py-2.5 text-sm text-zinc-300"
                onClick={closeModal}
              >
                Zavrieť
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
