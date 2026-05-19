"use client";

import { useEffect, useMemo, useState } from "react";

import { QsSelect } from "@/components/ui/qs-select";
import { InfoHint } from "@/components/hive/info-hint";
import { HiveApiError, hivePostJson, hivePutJson } from "@/lib/api";
import type { ForagerRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type ForagerSourceType = "youtube" | "rss" | "free_api" | "custom";

interface AgentTemplateLite {
  id: string;
  name: string;
  category: string;
}

interface ForagerFormState {
  name: string;
  icon: string;
  description: string;
  source_type: ForagerSourceType;
  source_config_json: string;
  filter_config_json: string;
  prompt_template: string;
  tools: string;
  is_active: boolean;
  agent_template_id: string;
  schedule_enabled: boolean;
  schedule_kind: "interval" | "cron" | "event";
  interval_seconds: number;
  cron_expr: string;
  runtime_mode: "durable" | "inprocess";
}

const TOOL_OPTIONS = ["web_search", "rss", "youtube", "wikipedia", "scrape_url", "coingecko"] as const;
const ICON_OPTIONS = ["🐝", "📺", "📰", "📡", "🔎", "🧠", "📊", "⚡", "🛠️", "🚀"] as const;
const SCHEDULE_PRESETS = [
  { label: "15 min", seconds: 900 },
  { label: "30 min", seconds: 1800 },
  { label: "1 hour", seconds: 3600 },
  { label: "4 hours", seconds: 14400 },
  { label: "12 hours", seconds: 43200 },
  { label: "24 hours", seconds: 86400 },
] as const;

const SCHEDULE_PRESET_OPTIONS = SCHEDULE_PRESETS.map((preset) => ({
  value: String(preset.seconds),
  label: preset.label,
}));

const SOURCE_TYPE_OPTIONS = [
  { value: "rss", label: "RSS" },
  { value: "youtube", label: "YouTube" },
  { value: "free_api", label: "Free API" },
  { value: "custom", label: "Custom" },
] as const;

const SCHEDULE_KIND_OPTIONS = [
  { value: "interval", label: "interval" },
  { value: "cron", label: "cron" },
  { value: "event", label: "event" },
] as const;

function createEmptyForm(): ForagerFormState {
  return {
    name: "",
    icon: "🐝",
    description: "",
    source_type: "rss",
    source_config_json: '{\n  "feeds": ["https://example.com/feed.xml"]\n}',
    filter_config_json: '{\n  "default_tags": ["market"]\n}',
    prompt_template: "",
    tools: "rss,web_search",
    is_active: true,
    agent_template_id: "",
    schedule_enabled: false,
    schedule_kind: "interval",
    interval_seconds: 900,
    cron_expr: "",
    runtime_mode: "durable",
  };
}

function parseJsonField(raw: string, fallback: Record<string, unknown>): Record<string, unknown> {
  const text = raw.trim();
  if (!text) return fallback;
  const parsed = JSON.parse(text);
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("Expected JSON object.");
  }
  return parsed as Record<string, unknown>;
}

function splitMultiline(raw: string): string[] {
  return raw
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinMultiline(items: unknown): string {
  if (!Array.isArray(items)) return "";
  return items
    .map((item) => String(item).trim())
    .filter(Boolean)
    .join("\n");
}

function inferIcon(sourceType: ForagerSourceType): string {
  if (sourceType === "youtube") return "📺";
  if (sourceType === "rss") return "📰";
  if (sourceType === "free_api") return "📡";
  return "🛠️";
}

export interface ForagerFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editingForager: ForagerRow | null;
  templates: AgentTemplateLite[];
  canManage: boolean;
  onSaved: () => void;
}

/** Create / edit forager modal — full CRUD form preserved from legacy page. */
export function ForagerFormDialog({
  open,
  onOpenChange,
  editingForager,
  templates,
  canManage,
  onSaved,
}: ForagerFormDialogProps) {
  const editingId = editingForager?.id ?? null;
  const templateSelectOptions = useMemo(
    () => [
      { value: "", label: "None" },
      ...templates.map((template) => ({
        value: template.id,
        label: `${template.name} (${template.category})`,
      })),
    ],
    [templates],
  );
  const [form, setForm] = useState<ForagerFormState>(createEmptyForm());
  const [configChannels, setConfigChannels] = useState("");
  const [configFeeds, setConfigFeeds] = useState("");
  const [configQueries, setConfigQueries] = useState("");
  const [configEndpoint, setConfigEndpoint] = useState("");
  const [saving, setSaving] = useState(false);

  const parsedTools = useMemo(
    () =>
      form.tools
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    [form.tools],
  );

  useEffect(() => {
    if (!open) return;
    if (!editingForager) {
      setForm(createEmptyForm());
      setConfigChannels("");
      setConfigFeeds("https://example.com/feed.xml");
      setConfigQueries("");
      setConfigEndpoint("");
      return;
    }
    const sourceType = (editingForager.source_type as ForagerSourceType) || "rss";
    setForm({
      name: editingForager.name,
      icon: editingForager.description.trim().charAt(0) || inferIcon(sourceType),
      description: editingForager.description,
      source_type: sourceType,
      source_config_json: JSON.stringify(editingForager.source_config || {}, null, 2),
      filter_config_json: JSON.stringify(editingForager.filter_config || {}, null, 2),
      prompt_template: editingForager.prompt_template || "",
      tools: (editingForager.tools || []).join(","),
      is_active: editingForager.is_active,
      agent_template_id: editingForager.agent_template_id || "",
      schedule_enabled: Boolean(editingForager.supervisor_routine_id),
      schedule_kind: "interval",
      interval_seconds: 900,
      cron_expr: "",
      runtime_mode: "durable",
    });
    setConfigChannels(joinMultiline((editingForager.source_config || {}).channels));
    setConfigFeeds(joinMultiline((editingForager.source_config || {}).feeds));
    setConfigQueries(joinMultiline((editingForager.source_config || {}).search_queries));
    setConfigEndpoint(String((editingForager.source_config || {}).endpoint || ""));
  }, [open, editingForager]);

  function buildStructuredSourceConfig(): Record<string, unknown> {
    if (form.source_type === "youtube") {
      return {
        channels: splitMultiline(configChannels),
        search_queries: splitMultiline(configQueries),
      };
    }
    if (form.source_type === "rss") {
      return {
        feeds: splitMultiline(configFeeds),
        search_queries: splitMultiline(configQueries),
      };
    }
    if (form.source_type === "free_api") {
      return {
        endpoint: configEndpoint.trim() || null,
        search_queries: splitMultiline(configQueries),
      };
    }
    return {};
  }

  function syncJsonFromStructuredFields() {
    const cfg = buildStructuredSourceConfig();
    setForm((prev) => ({ ...prev, source_config_json: JSON.stringify(cfg, null, 2) }));
  }

  function applyJsonIntoStructuredFields() {
    try {
      const parsed = parseJsonField(form.source_config_json, {});
      setConfigChannels(joinMultiline(parsed.channels));
      setConfigFeeds(joinMultiline(parsed.feeds));
      setConfigQueries(joinMultiline(parsed.search_queries));
      setConfigEndpoint(String(parsed.endpoint || ""));
    } catch {
      window.alert("Source config JSON is invalid.");
    }
  }

  async function saveForager() {
    if (!canManage) {
      window.alert("Only owner/admin can manage foragers.");
      return;
    }
    setSaving(true);
    try {
      const sourceConfigAdvanced = parseJsonField(form.source_config_json, {});
      const sourceConfigStructured = buildStructuredSourceConfig();
      const source_config =
        form.source_type === "custom"
          ? sourceConfigAdvanced
          : {
              ...sourceConfigAdvanced,
              ...sourceConfigStructured,
            };
      const filter_config = parseJsonField(form.filter_config_json, {});
      const payload = {
        name: form.name.trim(),
        description: `${form.icon} ${form.description.trim()}`.trim(),
        source_type: form.source_type,
        source_config,
        filter_config,
        prompt_template: form.prompt_template.trim(),
        tools: parsedTools,
        is_active: form.is_active,
        agent_template_id: form.agent_template_id || null,
        schedule: {
          enabled: form.schedule_enabled,
          schedule_kind: form.schedule_kind,
          interval_seconds: form.interval_seconds,
          cron_expr: form.cron_expr.trim() || null,
          runtime_mode: form.runtime_mode,
        },
      };
      if (!payload.name) {
        window.alert("Forager name is required.");
        return;
      }
      if (editingId) {
        await hivePutJson<ForagerRow>(`foragers/${encodeURIComponent(editingId)}`, payload);
      } else {
        await hivePostJson<ForagerRow>("foragers", payload);
      }
      onOpenChange(false);
      onSaved();
    } catch (err) {
      const message = err instanceof HiveApiError ? err.message : err instanceof Error ? err.message : "Forager save failed.";
      window.alert(message);
    } finally {
      setSaving(false);
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
      onClick={() => onOpenChange(false)}
      role="presentation"
    >
      <div
        className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-[color:var(--qs-border-2)] bg-[#070d16] p-5"
        style={{ borderRadius: "var(--qs-radius-lg)" }}
        onClick={(event) => event.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-zinc-100">{editingId ? "Edit forager" : "Create forager"}</h2>

        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-zinc-400">Name</label>
              <InfoHint
                title="Forager name"
                description="Human-readable name shown in cards, routines, and logs."
                options={["Use domain-oriented naming", "Keep names unique per tenant"]}
              />
            </div>
            <input
              value={form.name}
              onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
              className="mt-1 w-full rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-pollen/50"
            />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-zinc-400">Icon</label>
              <InfoHint
                title="Forager icon"
                description="Visual marker for quick recognition in the card grid."
                options={["Emoji picker", "Can be changed anytime"]}
              />
            </div>
            <div className="mt-1 grid grid-cols-5 gap-1.5">
              {ICON_OPTIONS.map((icon) => (
                <button
                  key={icon}
                  type="button"
                  onClick={() => setForm((prev) => ({ ...prev, icon }))}
                  className={cn(
                    "rounded-md border px-2 py-1 text-base",
                    form.icon === icon ? "border-pollen/60 bg-pollen/15" : "border-white/15 bg-black/30",
                  )}
                >
                  {icon}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-zinc-400">Type</label>
              <InfoHint
                title="Forager type"
                description="Source mode determines structured configuration fields."
                options={["YouTube channels", "RSS feeds", "Free API endpoint", "Custom JSON mode"]}
              />
            </div>
            <QsSelect
              value={form.source_type}
              onValueChange={(next) =>
                setForm((prev) => {
                  const nextType = next as ForagerSourceType;
                  return {
                    ...prev,
                    source_type: nextType,
                    icon: prev.icon === "🐝" ? inferIcon(nextType) : prev.icon,
                  };
                })
              }
              className="mt-1 w-full"
              options={SOURCE_TYPE_OPTIONS}
            />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-zinc-400">Enabled</label>
              <InfoHint
                title="Enabled/Disabled"
                description="Disabled foragers stay in library but do not run routines."
                options={["Use disable for temporary maintenance windows"]}
              />
            </div>
            <label className="mt-3 inline-flex items-center gap-2 text-xs text-zinc-300">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) => setForm((prev) => ({ ...prev, is_active: event.target.checked }))}
              />
              Forager enabled
            </label>
          </div>
        </div>

        <div className="mt-3">
          <div className="flex items-center gap-2">
            <label className="text-xs text-zinc-400">Description</label>
            <InfoHint
              title="Description"
              description="Short mission note for operators and future editors."
              options={["Scope", "Signal type", "Expected output"]}
            />
          </div>
          <textarea
            rows={2}
            value={form.description}
            onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
            className="mt-1 w-full resize-y rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-pollen/50"
          />
        </div>

        {form.source_type === "youtube" ? (
          <div className="mt-3 rounded-xl border border-white/10 bg-black/25 p-3">
            <label className="text-xs text-zinc-400">YouTube channels (one per line)</label>
            <textarea
              rows={3}
              value={configChannels}
              onChange={(event) => setConfigChannels(event.target.value)}
              className="mt-1 w-full resize-y rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-xs text-zinc-100 outline-none focus:border-[color:var(--qs-border-2)]"
            />
            <label className="mt-2 block text-xs text-zinc-400">Search queries (one per line)</label>
            <textarea
              rows={2}
              value={configQueries}
              onChange={(event) => setConfigQueries(event.target.value)}
              className="mt-1 w-full resize-y rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-xs text-zinc-100 outline-none focus:border-[color:var(--qs-border-2)]"
            />
          </div>
        ) : null}

        {form.source_type === "rss" ? (
          <div className="mt-3 rounded-xl border border-white/10 bg-black/25 p-3">
            <label className="text-xs text-zinc-400">RSS feeds (one URL per line)</label>
            <textarea
              rows={4}
              value={configFeeds}
              onChange={(event) => setConfigFeeds(event.target.value)}
              className="mt-1 w-full resize-y rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-xs text-zinc-100 outline-none focus:border-[color:var(--qs-border-2)]"
            />
            <label className="mt-2 block text-xs text-zinc-400">Search queries (one per line)</label>
            <textarea
              rows={2}
              value={configQueries}
              onChange={(event) => setConfigQueries(event.target.value)}
              className="mt-1 w-full resize-y rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-xs text-zinc-100 outline-none focus:border-[color:var(--qs-border-2)]"
            />
          </div>
        ) : null}

        {form.source_type === "free_api" ? (
          <div className="mt-3 rounded-xl border border-white/10 bg-black/25 p-3">
            <label className="text-xs text-zinc-400">API endpoint</label>
            <input
              value={configEndpoint}
              onChange={(event) => setConfigEndpoint(event.target.value)}
              placeholder="https://api.example.com/v1/search"
              className="mt-1 w-full rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-xs text-zinc-100 outline-none focus:border-[color:var(--qs-border-2)]"
            />
            <label className="mt-2 block text-xs text-zinc-400">Search queries (one per line)</label>
            <textarea
              rows={2}
              value={configQueries}
              onChange={(event) => setConfigQueries(event.target.value)}
              className="mt-1 w-full resize-y rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-xs text-zinc-100 outline-none focus:border-[color:var(--qs-border-2)]"
            />
          </div>
        ) : null}

        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <div>
            <label className="text-xs text-zinc-400">Source config (JSON)</label>
            <textarea
              rows={6}
              value={form.source_config_json}
              onChange={(event) => setForm((prev) => ({ ...prev, source_config_json: event.target.value }))}
              className="mt-1 w-full resize-y rounded-lg border border-white/15 bg-black/40 px-3 py-2 font-mono text-xs text-zinc-100 outline-none focus:border-[color:var(--qs-border-2)]"
            />
            <div className="mt-2 flex gap-2">
              <button
                type="button"
                onClick={syncJsonFromStructuredFields}
                className="rounded border border-data/45 bg-cyan/10 px-2 py-1 text-[10px] font-semibold text-cyan"
              >
                Sync JSON from fields
              </button>
              <button
                type="button"
                onClick={applyJsonIntoStructuredFields}
                className="rounded border border-white/25 bg-black/35 px-2 py-1 text-[10px] font-semibold text-zinc-200"
              >
                Apply JSON to fields
              </button>
            </div>
          </div>
          <div>
            <label className="text-xs text-zinc-400">Filter config (JSON)</label>
            <textarea
              rows={6}
              value={form.filter_config_json}
              onChange={(event) => setForm((prev) => ({ ...prev, filter_config_json: event.target.value }))}
              className="mt-1 w-full resize-y rounded-lg border border-white/15 bg-black/40 px-3 py-2 font-mono text-xs text-zinc-100 outline-none focus:border-[color:var(--qs-border-2)]"
            />
          </div>
        </div>

        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <div>
            <label className="text-xs text-zinc-400">Tools</label>
            <input
              value={form.tools}
              onChange={(event) => setForm((prev) => ({ ...prev, tools: event.target.value }))}
              className="mt-1 w-full rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-pollen/50"
            />
            <div className="mt-1 flex flex-wrap gap-1">
              {TOOL_OPTIONS.map((tool) => {
                const selected = parsedTools.includes(tool);
                return (
                  <button
                    key={tool}
                    type="button"
                    onClick={() =>
                      setForm((prev) => {
                        const values = prev.tools
                          .split(",")
                          .map((item) => item.trim())
                          .filter(Boolean);
                        const next = values.includes(tool) ? values.filter((item) => item !== tool) : [...values, tool];
                        return { ...prev, tools: next.join(",") };
                      })
                    }
                    className={cn(
                      "rounded border px-1.5 py-0.5 text-[10px]",
                      selected ? "border-[color:var(--qs-border-2)] bg-cyan/10 text-cyan" : "border-white/15 text-zinc-400",
                    )}
                  >
                    {tool}
                  </button>
                );
              })}
            </div>
          </div>
          <div>
            <label className="text-xs text-zinc-400">Agent template</label>
            <QsSelect
              value={form.agent_template_id}
              onValueChange={(next) => setForm((prev) => ({ ...prev, agent_template_id: next }))}
              className="mt-1 w-full"
              options={templateSelectOptions}
            />
          </div>
        </div>

        <div className="mt-3 rounded-xl border border-white/10 bg-black/25 p-3">
          <label className="text-xs text-zinc-200">Frequency and routine</label>
          <label className="mt-2 inline-flex items-center gap-2 text-xs text-zinc-300">
            <input
              type="checkbox"
              checked={form.schedule_enabled}
              onChange={(event) => setForm((prev) => ({ ...prev, schedule_enabled: event.target.checked }))}
            />
            Enable periodic routine
          </label>
          {form.schedule_enabled ? (
            <div className="mt-2 grid gap-2 md:grid-cols-3">
              <QsSelect
                value={form.schedule_kind}
                onValueChange={(next) =>
                  setForm((prev) => ({ ...prev, schedule_kind: next as "interval" | "cron" | "event" }))
                }
                options={SCHEDULE_KIND_OPTIONS}
              />
              <QsSelect
                value={String(form.interval_seconds)}
                onValueChange={(next) =>
                  setForm((prev) => ({ ...prev, interval_seconds: Number(next) || 900 }))
                }
                options={SCHEDULE_PRESET_OPTIONS}
              />
              <input
                value={form.cron_expr}
                onChange={(event) => setForm((prev) => ({ ...prev, cron_expr: event.target.value }))}
                placeholder="@daily"
                className="rounded-lg border border-white/15 bg-black/40 px-2 py-1.5 text-xs text-zinc-100"
              />
            </div>
          ) : null}
        </div>

        <div className="mt-3">
          <label className="text-xs text-zinc-400">Prompt template</label>
          <textarea
            rows={4}
            value={form.prompt_template}
            onChange={(event) => setForm((prev) => ({ ...prev, prompt_template: event.target.value }))}
            className="mt-1 w-full resize-y rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-[color:var(--qs-border-2)]"
          />
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button type="button" onClick={() => onOpenChange(false)} className="qs-btn qs-btn--ghost qs-btn--sm">
            Cancel
          </button>
          <button type="button" onClick={() => void saveForager()} disabled={saving} className="qs-btn qs-btn--primary qs-btn--sm">
            {saving ? "Saving…" : editingId ? "Save changes" : "Create forager"}
          </button>
        </div>
      </div>
    </div>
  );
}
