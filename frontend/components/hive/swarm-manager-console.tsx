"use client";

import { useCallback, useEffect, useState } from "react";

import { cn } from "@/lib/utils";

const SWARM_COLORS = [
  "#00E5FF",
  "#FFB800",
  "#FF00AA",
  "#00FF88",
  "#FF3366",
  "#A855F7",
  "#F97316",
  "#06B6D4",
] as const;

const SWARM_ROLE_PRESETS = [
  { id: "scout", label: "Scout", desc: "Scrapes web, YouTube, RSS, APIs for raw data" },
  { id: "eval", label: "Evaluator", desc: "Fact-checks, scores and validates scraped data" },
  { id: "sim", label: "Simulator", desc: "Runs what-if scenarios before committing actions" },
  { id: "action", label: "Action", desc: "Posts, trades, reports and executes decisions" },
  { id: "custom", label: "Custom", desc: "Define your own role via prompt" },
] as const;

type PurposeApi = "scout" | "eval" | "simulation" | "action";

interface SubSwarmApi {
  id: string;
  name: string;
  purpose: string;
  local_memory?: Record<string, unknown>;
  member_count?: number;
  is_active?: boolean;
}

interface AgentApi {
  id: string;
  name: string;
  swarm_id?: string | null;
  status: string;
}

function purposeForPreset(presetId: string, customRole: string): PurposeApi {
  if (presetId === "scout") return "scout";
  if (presetId === "eval") return "eval";
  if (presetId === "sim") return "simulation";
  return "action";
}

function defaultColorForPurpose(purpose: string): string {
  const p = purpose.toLowerCase();
  if (p.includes("scout")) return "#00E5FF";
  if (p.includes("eval")) return "#FFB800";
  if (p.includes("sim")) return "#FF00AA";
  return "#00FF88";
}

function displayRole(swarm: SubSwarmApi): string {
  const lm = swarm.local_memory ?? {};
  const hi = (lm.hive_ui as Record<string, unknown> | undefined) ?? {};
  const label = (hi.swarm_role_label as string) || (lm.swarm_role_label as string);
  if (label?.trim()) return label;
  return String(swarm.purpose ?? "swarm");
}

function displayColor(swarm: SubSwarmApi): string {
  const lm = swarm.local_memory ?? {};
  const hi = (lm.hive_ui as Record<string, unknown> | undefined) ?? {};
  const hex = (hi.swarm_color_hex as string) || (lm.swarm_color_hex as string);
  if (hex?.startsWith("#")) return hex;
  return defaultColorForPurpose(String(swarm.purpose));
}

export function SwarmManagerConsole() {
  const [swarms, setSwarms] = useState<SubSwarmApi[]>([]);
  const [agents, setAgents] = useState<AgentApi[]>([]);
  const [creating, setCreating] = useState(false);
  const [assigningTo, setAssigningTo] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [form, setForm] = useState({
    name: "",
    role: "scout" as (typeof SWARM_ROLE_PRESETS)[number]["id"],
    color: "#00E5FF",
    system_prompt: "",
    custom_role: "",
  });

  const loadAll = useCallback(async () => {
    try {
      const [sRes, aRes] = await Promise.all([
        fetch("/api/proxy/swarms?limit=200", { credentials: "include" }).then((r) =>
          r.ok ? r.json() : null,
        ),
        fetch("/api/proxy/agents?limit=200", { credentials: "include" }).then((r) =>
          r.ok ? r.json() : null,
        ),
      ]);

      let sList = sRes?.swarms ?? sRes?.items;
      if (!Array.isArray(sList)) {
        sList = Array.isArray(sRes) ? sRes : [];
      }
      setSwarms(
        (sList as SubSwarmApi[]).filter(
          (s) => s && s.is_active !== false && String(s.name).includes("__inactive_") === false,
        ),
      );

      let aList = aRes?.agents ?? aRes?.items;
      if (!Array.isArray(aList)) {
        aList = Array.isArray(aRes) ? aRes : [];
      }
      setAgents(aList as AgentApi[]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAll();
    const iv = window.setInterval(() => void loadAll(), 10000);
    return () => window.clearInterval(iv);
  }, [loadAll]);

  async function createSwarm() {
    if (!form.name.trim()) return;

    const preset = SWARM_ROLE_PRESETS.find((p) => p.id === form.role);
    const roleLabel = form.role === "custom" ? form.custom_role.trim() || "Custom" : preset?.label ?? form.role;

    const defaultPrompt =
      preset && form.role !== "custom"
        ? `You are a ${preset.label} swarm manager. ${preset.desc}. Coordinate your assigned agents to achieve the given task efficiently.`
        : "";

    const systemPrompt =
      form.system_prompt.trim() || defaultPrompt || "You coordinate assigned agents efficiently for operator tasks.";

    const purpose = purposeForPreset(form.role, form.custom_role);

    const local_memory = {
      swarm_role_label: roleLabel,
      swarm_color_hex: form.color,
      manager_system_prompt: systemPrompt,
      hive_ui: {
        swarm_role_label: roleLabel,
        swarm_color_hex: form.color,
        manager_system_prompt: systemPrompt,
      },
    };

    const r = await fetch("/api/proxy/swarms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        name: form.name.trim(),
        purpose,
        local_memory,
        is_active: true,
      }),
    });
    if (r.ok) {
      setCreating(false);
      setForm({ name: "", role: "scout", color: "#00E5FF", system_prompt: "", custom_role: "" });
      await loadAll();
    } else {
      let msg = "Failed to create swarm";
      try {
        const e = await r.json();
        msg = typeof e?.detail === "string" ? e.detail : JSON.stringify(e?.detail ?? e);
      } catch {
        /* ignore */
      }
      window.alert(msg);
    }
  }

  async function deleteSwarm(id: string) {
    if (!window.confirm("Delete this swarm? Agents will become unassigned.")) return;
    const r = await fetch(`/api/proxy/swarms/${encodeURIComponent(id)}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (!r.ok) {
      let msg = "Delete failed";
      try {
        const e = await r.json();
        msg = typeof e?.detail === "string" ? e.detail : JSON.stringify(e?.detail ?? e);
      } catch {
        /* ignore */
      }
      window.alert(msg);
    } else {
      try {
        const body = await r.json();
        if (body?.mode === "archived") {
          window.alert("Swarm archived (workflow history present). Bees were unassigned; name freed for reuse.");
        }
      } catch {
        /* ignore */
      }
    }
    await loadAll();
  }

  async function assignAgent(agentId: string, swarmId: string | null) {
    const body =
      swarmId === null ? { detach_from_swarm: true } : { detach_from_swarm: false, swarm_id: swarmId };
    await fetch(`/api/proxy/agents/${encodeURIComponent(agentId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(body),
    });
    await loadAll();
  }

  async function wakeSwarm(swarmId: string) {
    await fetch(`/api/proxy/swarms/${encodeURIComponent(swarmId)}/wake`, {
      method: "POST",
      credentials: "include",
    });
    await loadAll();
  }

  const unassigned = agents.filter((a) => !a.swarm_id);

  function assignableToSwarm(swarmId: string): AgentApi[] {
    return agents.filter((a) => a.swarm_id !== swarmId);
  }

  function swarmLabelById(swarmId: string | null | undefined): string | null {
    if (!swarmId) return null;
    return swarms.find((s) => s.id === swarmId)?.name ?? "other swarm";
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="font-[family-name:var(--font-poppins)] text-xl font-bold text-[#fafafa]">
            Swarm cockpit
          </h2>
          <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
            {swarms.length} swarms · {agents.length - unassigned.length} assigned · {unassigned.length} unassigned
          </p>
        </div>
        <button
          type="button"
          onClick={() => setCreating(true)}
          className="rounded-xl border-2 border-pollen bg-pollen px-4 py-2 font-[family-name:var(--font-poppins)] text-xs font-bold text-black shadow-[0_0_24px_rgb(255_184_0/0.35)]"
        >
          + New swarm
        </button>
      </div>

      {creating ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          role="dialog"
          aria-modal
          onClick={() => setCreating(false)}
          onKeyDown={(e) => e.key === "Escape" && setCreating(false)}
        >
          <div
            className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-3xl border border-pollen/30 bg-[#0f0f1a] p-6 shadow-[0_0_48px_rgb(255_184_0/0.15)]"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="font-[family-name:var(--font-poppins)] text-lg font-bold text-[#fafafa]">
              Create new swarm
            </h3>
            <label className="mt-6 block font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-bold uppercase tracking-widest text-zinc-500">
              Swarm name
            </label>
            <input
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Crypto Scout"
              className="mt-2 w-full rounded-xl border border-white/15 bg-black/55 px-3 py-2.5 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] outline-none focus:border-pollen/50"
            />
            <label className="mt-5 block font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-bold uppercase tracking-widest text-zinc-500">
              Role lane
            </label>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {SWARM_ROLE_PRESETS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, role: p.id }))}
                  className={cn(
                    "rounded-xl border px-3 py-2 text-left transition",
                    form.role === p.id
                      ? "border-pollen/50 bg-pollen/[0.08] text-pollen"
                      : "border-white/10 bg-black/35 text-zinc-400 hover:border-white/20",
                  )}
                >
                  <div className="font-[family-name:var(--font-inter)] text-sm font-semibold">{p.label}</div>
                  <div className="mt-1 font-[family-name:var(--font-inter)] text-[11px] text-zinc-500">{p.desc}</div>
                </button>
              ))}
            </div>
            {form.role === "custom" ? (
              <>
                <label className="mt-5 block font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-bold uppercase tracking-widest text-zinc-500">
                  Custom role name
                </label>
                <input
                  value={form.custom_role}
                  onChange={(e) => setForm((f) => ({ ...f, custom_role: e.target.value }))}
                  placeholder="e.g. Content Writer"
                  className="mt-2 w-full rounded-xl border border-white/15 bg-black/55 px-3 py-2.5 text-sm text-[#fafafa] outline-none focus:border-pollen/50"
                />
              </>
            ) : null}
            <label className="mt-5 block font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-bold uppercase tracking-widest text-zinc-500">
              Accent color
            </label>
            <div className="mt-2 flex flex-wrap gap-2">
              {SWARM_COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  aria-label={`Color ${c}`}
                  onClick={() => setForm((f) => ({ ...f, color: c }))}
                  className={cn(
                    "h-8 w-8 rounded-lg border border-white/15 transition ring-offset-2 ring-offset-[#0f0f1a]",
                    form.color === c ? "scale-105 ring-2 ring-white" : "opacity-80 hover:opacity-100",
                  )}
                  style={{ backgroundColor: c, boxShadow: form.color === c ? `0 0 14px ${c}88` : undefined }}
                />
              ))}
            </div>
            <label className="mt-5 block font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-bold uppercase tracking-widest text-zinc-500">
              Manager prompt (optional)
            </label>
            <textarea
              value={form.system_prompt}
              onChange={(e) => setForm((f) => ({ ...f, system_prompt: e.target.value }))}
              rows={4}
              className="mt-2 w-full resize-y rounded-xl border border-white/15 bg-black/55 px-3 py-2.5 font-[family-name:var(--font-jetbrains-mono)] text-xs text-[#fafafa] outline-none focus:border-cyan/40"
            />
            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={() => setCreating(false)}
                className="flex-1 rounded-xl border border-white/15 px-4 py-2.5 font-[family-name:var(--font-inter)] text-sm font-semibold text-zinc-400"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void createSwarm()}
                className="flex-[2] rounded-xl bg-pollen py-2.5 font-[family-name:var(--font-poppins)] text-sm font-bold text-black shadow-[0_0_26px_rgb(255_184_0/0.35)]"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {loading ? (
        <p className="py-14 text-center text-sm text-zinc-500">Loading swarms…</p>
      ) : swarms.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-cyan/20 bg-black/35 p-14 text-center">
          <div className="text-4xl opacity-70" aria-hidden>
            🔗
          </div>
          <p className="mt-4 font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#fafafa]">
            No swarms yet
          </p>
          <p className="mt-2 text-sm text-zinc-500">Create one, then attach bees.</p>
          <button
            type="button"
            onClick={() => setCreating(true)}
            className="mt-6 rounded-xl bg-pollen px-5 py-2.5 font-[family-name:var(--font-poppins)] text-sm font-bold text-black"
          >
            Create first swarm
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {swarms.map((swarm) => {
            const color = displayColor(swarm);
            const role = displayRole(swarm);
            const members = agents.filter((a) => a.swarm_id === swarm.id);
            const active = members.filter((a) => a.status === "active" || a.status === "running").length;
            return (
              <div
                key={swarm.id}
                className="rounded-3xl border border-white/[0.08] bg-[#0f0f16]/95 p-5 shadow-[0_0_32px_rgb(0_0_0/0.25)] md:p-6"
                style={{
                  borderLeftWidth: "3px",
                  borderLeftColor: color,
                }}
              >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="flex min-w-0 items-start gap-3">
                    <div
                      className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border text-lg"
                      style={{
                        borderColor: `${color}55`,
                        backgroundColor: `${color}18`,
                        color,
                      }}
                    >
                      🔗
                    </div>
                    <div className="min-w-0">
                      <div className="font-[family-name:var(--font-poppins)] font-bold text-[#fafafa]">
                        {swarm.name}
                      </div>
                      <div className="mt-1 font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-500">
                        {role} · {members.length} agents · {active} active/run
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => void wakeSwarm(swarm.id)}
                      className="rounded-xl border px-3 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[11px] font-semibold"
                      style={{
                        borderColor: `${color}55`,
                        backgroundColor: `${color}14`,
                        color,
                      }}
                    >
                      Wake
                    </button>
                    <button
                      type="button"
                      onClick={() => setAssigningTo((x) => (x === swarm.id ? null : swarm.id))}
                      className="rounded-xl border border-white/15 bg-transparent px-3 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-300 hover:border-pollen/30"
                    >
                      + Assign bees
                    </button>
                    <button
                      type="button"
                      onClick={() => void deleteSwarm(swarm.id)}
                      className="rounded-xl border border-danger/35 bg-transparent px-3 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-danger"
                    >
                      Delete
                    </button>
                  </div>
                </div>

                {members.length ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {members.map((agent) => (
                      <div
                        key={agent.id}
                        className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/40 px-3 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-300"
                      >
                        <span
                          className="h-1.5 w-1.5 rounded-full"
                          style={{
                            background:
                              agent.status === "active" || agent.status === "running" ? "#00FF88" : "#FFB800",
                          }}
                        />
                        <span>{agent.name}</span>
                        <button
                          type="button"
                          aria-label={`Unassign ${agent.name}`}
                          onClick={() => void assignAgent(agent.id, null)}
                          className="text-zinc-500 hover:text-zinc-300"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                ) : null}

                {assigningTo === swarm.id && assignableToSwarm(swarm.id).length > 0 ? (
                  <div className="mt-4 border-t border-white/[0.06] pt-4">
                    <p className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500">
                      AVAILABLE BEES — attach to {swarm.name}{" "}
                      <span className="normal-case text-zinc-600">
                        (unassigned or from another swarm — click to move)
                      </span>
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {assignableToSwarm(swarm.id).map((agent) => {
                        const fromName = swarmLabelById(agent.swarm_id);
                        return (
                          <button
                            key={agent.id}
                            type="button"
                            onClick={() => void assignAgent(agent.id, swarm.id)}
                            className="flex max-w-full flex-wrap items-center gap-x-1 rounded-xl border px-3 py-1.5 text-left font-[family-name:var(--font-jetbrains-mono)] text-[11px]"
                            style={{
                              borderColor: `${color}55`,
                              backgroundColor: `${color}12`,
                              color,
                            }}
                          >
                            <span>+ {agent.name}</span>
                            {agent.swarm_id && agent.swarm_id !== swarm.id ? (
                              <span className="truncate text-[10px] normal-case text-zinc-500">
                                (from {fromName ?? "other"})
                              </span>
                            ) : null}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ) : null}
                {assigningTo === swarm.id && assignableToSwarm(swarm.id).length === 0 ? (
                  <div className="mt-4 border-t border-white/[0.06] pt-3 text-sm text-zinc-500">
                    All agents are already in this swarm.
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}

      {unassigned.length > 0 ? (
        <div className="rounded-3xl border border-white/[0.06] bg-black/35 p-5">
          <p className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-zinc-300">
            Unassigned agents ({unassigned.length})
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {unassigned.map((a) => (
              <span
                key={a.id}
                className="rounded-lg border border-white/10 px-3 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500"
              >
                {a.name}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
