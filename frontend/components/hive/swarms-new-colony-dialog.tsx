"use client";

import { X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";

const SWARM_COLORS = ["#00E5FF", "#FFB800", "#FF00AA", "#00FF88", "#A855F7", "#F97316"] as const;

const SWARM_ROLE_PRESETS = [
  { id: "scout", label: "Scout", desc: "Scrapes web, YouTube, RSS, APIs for raw data" },
  { id: "eval", label: "Evaluator", desc: "Fact-checks, scores and validates scraped data" },
  { id: "sim", label: "Simulator", desc: "Runs what-if scenarios before committing actions" },
  { id: "action", label: "Action", desc: "Posts, trades, reports and executes decisions" },
  { id: "custom", label: "Custom", desc: "Define your own role via prompt" },
] as const;

type PurposeApi = "scout" | "eval" | "simulation" | "action";

function purposeForPreset(presetId: string): PurposeApi {
  if (presetId === "scout") return "scout";
  if (presetId === "eval") return "eval";
  if (presetId === "sim") return "simulation";
  return "action";
}

interface SwarmsNewColonyDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

/** V4 modal — create sub-swarm colony via POST /swarms. */
export function SwarmsNewColonyDialog({ open, onClose, onCreated }: SwarmsNewColonyDialogProps) {
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    name: "",
    role: "scout" as (typeof SWARM_ROLE_PRESETS)[number]["id"],
    color: SWARM_COLORS[0] as string,
    system_prompt: "",
    custom_role: "",
  });

  if (!open) {
    return null;
  }

  async function handleCreate(): Promise<void> {
    if (!form.name.trim()) {
      toast.error("Colony name is required");
      return;
    }
    const preset = SWARM_ROLE_PRESETS.find((p) => p.id === form.role);
    const roleLabel = form.role === "custom" ? form.custom_role.trim() || "Custom" : preset?.label ?? form.role;
    const defaultPrompt =
      preset && form.role !== "custom"
        ? `You are a ${preset.label} swarm manager. ${preset.desc}. Coordinate your assigned agents to achieve the given task efficiently.`
        : "";
    const systemPrompt =
      form.system_prompt.trim() || defaultPrompt || "You coordinate assigned agents efficiently for operator tasks.";
    const purpose = purposeForPreset(form.role);
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

    setBusy(true);
    try {
      const res = await fetch("/api/proxy/swarms", {
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
      if (!res.ok) {
        let msg = "Failed to create colony";
        try {
          const e = (await res.json()) as { detail?: unknown };
          msg = typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail ?? e);
        } catch {
          /* ignore */
        }
        toast.error(msg);
        return;
      }
      toast.success("Colony created");
      setForm({ name: "", role: "scout", color: SWARM_COLORS[0], system_prompt: "", custom_role: "" });
      onCreated();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-[220] flex items-center justify-center bg-[rgba(5,5,16,0.82)] p-4"
      role="dialog"
      aria-modal
      onClick={onClose}
      onKeyDown={(e) => e.key === "Escape" && onClose()}
    >
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-[var(--qs-radius-lg)] border border-[rgba(253,185,39,0.28)] bg-[var(--qs-surface)] p-6 shadow-[0_12px_40px_rgba(0,0,0,0.5)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-6 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-(--qs-text)">New colony</h2>
            <p className="mt-1 text-sm text-(--qs-text-3)">Stand up a local hive mind partition before assigning bees.</p>
          </div>
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" aria-label="Close" onClick={onClose}>
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>

        <label className="qs-label">Colony name</label>
        <input
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          placeholder="e.g. Alpha · Onboarding Lab"
          className="qs-input mt-2 w-full"
        />

        <p className="qs-label mt-5">Role lane</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {SWARM_ROLE_PRESETS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setForm((f) => ({ ...f, role: p.id }))}
              className={cn(
                "rounded-[var(--qs-radius-sm)] border px-3 py-2 text-left transition",
                form.role === p.id
                  ? "border-[rgba(253,185,39,0.45)] bg-[rgba(253,185,39,0.08)] text-pollen"
                  : "border-(--qs-border) bg-white/[0.02] text-(--qs-text-3) hover:border-(--qs-border-2)",
              )}
            >
              <div className="text-sm font-semibold">{p.label}</div>
              <div className="mt-1 text-[11px] opacity-80">{p.desc}</div>
            </button>
          ))}
        </div>

        {form.role === "custom" ? (
          <>
            <label className="qs-label mt-5">Custom role name</label>
            <input
              value={form.custom_role}
              onChange={(e) => setForm((f) => ({ ...f, custom_role: e.target.value }))}
              placeholder="e.g. Content Writer"
              className="qs-input mt-2 w-full"
            />
          </>
        ) : null}

        <label className="qs-label mt-5">Accent color</label>
        <div className="mt-2 flex flex-wrap gap-2">
          {SWARM_COLORS.map((c) => (
            <button
              key={c}
              type="button"
              aria-label={`Color ${c}`}
              onClick={() => setForm((f) => ({ ...f, color: c }))}
              className={cn(
                "h-8 w-8 rounded-full border-2 transition",
                form.color === c ? "border-white scale-110" : "border-transparent opacity-70 hover:opacity-100",
              )}
              style={{ backgroundColor: c }}
            />
          ))}
        </div>

        <div className="mt-6 flex flex-wrap justify-end gap-2">
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" disabled={busy} onClick={() => void handleCreate()}>
            {busy ? "Creating…" : "Create colony"}
          </button>
        </div>
      </div>
    </div>
  );
}
