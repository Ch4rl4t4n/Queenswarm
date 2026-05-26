"use client";

import { GitBranch, Plus, Trash2, Zap } from "lucide-react";
import type { JSX } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, V4CardHeader } from "@/components/ui/v4";
import type { DynamicConnectorPayload } from "@/lib/connectors-types";
import { HiveApiError, hiveDelete, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

interface SuperToolRouterRow {
  id: string;
  name: string;
  slug: string;
  description: string;
  is_active: boolean;
  routing_mode: "priority" | "research_then_action" | "parallel_hint";
  manager_slugs: string[];
  connector_slugs: string[];
  max_cost_tier?: "low" | "medium" | "high" | null;
  fallback_builtin_search: boolean;
}

interface RouterPreset {
  preset_id: string;
  title: string;
  description: string;
  routing_mode: string;
  manager_slugs: string[];
  connector_slugs: string[];
}

interface SuperRouterListResponse {
  items: SuperToolRouterRow[];
  presets: RouterPreset[];
}

interface ConnectorsEnvelope {
  items: DynamicConnectorPayload[];
}

const MANAGER_LANES = [
  { value: "research_intelligence", label: "Research Intelligence" },
  { value: "execution_operations", label: "Execution Operations" },
  { value: "content_creation", label: "Content Creation" },
  { value: "review_quality", label: "Review Quality" },
  { value: "personal_life", label: "Personal Life" },
  { value: "optimization", label: "Optimization" },
] as const;

const ROUTING_MODES = [
  { value: "priority", label: "Priority — first connector wins" },
  { value: "research_then_action", label: "Research → action (data first)" },
  { value: "parallel_hint", label: "Parallel hint — expose all, agent picks" },
] as const;

const SUGGESTED_CONNECTORS = [
  "monid_mcp",
  "apify_store",
  "composio_router",
  "nango_hub",
  "merge_agent_handler",
  "venice_mcp",
  "slack_web_api",
  "notion_workspace",
  "stripe_billing",
];

function routingLabel(mode: string): string {
  return ROUTING_MODES.find((row) => row.value === mode)?.label ?? mode;
}

export function SuperToolRouterPanel(): JSX.Element {
  const [routers, setRouters] = useState<SuperToolRouterRow[]>([]);
  const [presets, setPresets] = useState<RouterPreset[]>([]);
  const [installedSlugs, setInstalledSlugs] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [routingMode, setRoutingMode] = useState<(typeof ROUTING_MODES)[number]["value"]>("priority");
  const [managerSlugs, setManagerSlugs] = useState<string[]>(["research_intelligence"]);
  const [connectorSlugs, setConnectorSlugs] = useState<string[]>([]);
  const [isActive, setIsActive] = useState(false);
  const [fallbackSearch, setFallbackSearch] = useState(true);

  const connectorOptions = useMemo(() => {
    const merged = new Set([...SUGGESTED_CONNECTORS, ...installedSlugs]);
    return [...merged].sort().map((value) => ({ value, label: value }));
  }, [installedSlugs]);

  const load = useCallback(async (): Promise<void> => {
    setError(null);
    try {
      const [routersPayload, connectorsPayload] = await Promise.all([
        hiveGet<SuperRouterListResponse>("tools/super-routers"),
        hiveGet<ConnectorsEnvelope>("connectors/dynamic"),
      ]);
      setRouters(routersPayload.items ?? []);
      setPresets(routersPayload.presets ?? []);
      setInstalledSlugs(
        (connectorsPayload.items ?? [])
          .filter((row) => !row.is_builtin)
          .map((row) => row.slug.trim().toLowerCase()),
      );
    } catch (exc) {
      setError(exc instanceof HiveApiError ? exc.message : "Super routers unavailable.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function resetForm(): void {
    setEditId(null);
    setName("");
    setSlug("");
    setDescription("");
    setRoutingMode("priority");
    setManagerSlugs(["research_intelligence"]);
    setConnectorSlugs([]);
    setIsActive(false);
    setFallbackSearch(true);
  }

  function openCreate(): void {
    resetForm();
    setEditorOpen(true);
  }

  function openEdit(row: SuperToolRouterRow): void {
    setEditId(row.id);
    setName(row.name);
    setSlug(row.slug);
    setDescription(row.description);
    setRoutingMode(row.routing_mode);
    setManagerSlugs(row.manager_slugs);
    setConnectorSlugs(row.connector_slugs);
    setIsActive(row.is_active);
    setFallbackSearch(row.fallback_builtin_search);
    setEditorOpen(true);
  }

  function toggleManager(value: string): void {
    setManagerSlugs((prev) => (prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]));
  }

  function toggleConnector(value: string): void {
    setConnectorSlugs((prev) => (prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]));
  }

  async function saveRouter(): Promise<void> {
    if (!name.trim() || !slug.trim() || connectorSlugs.length === 0) {
      setError("Name, slug, and at least one connector are required.");
      return;
    }
    setBusyId("save");
    setError(null);
    setSuccess(null);
    try {
      const body = {
        name: name.trim(),
        slug: slug.trim().toLowerCase(),
        description: description.trim(),
        routing_mode: routingMode,
        manager_slugs: managerSlugs,
        connector_slugs: connectorSlugs,
        is_active: isActive,
        fallback_builtin_search: fallbackSearch,
      };
      if (editId) {
        await hivePatchJson(`tools/super-routers/${encodeURIComponent(editId)}`, body);
        setSuccess("Super router updated.");
      } else {
        await hivePostJson("tools/super-routers", body);
        setSuccess("Super router created.");
      }
      setEditorOpen(false);
      resetForm();
      await load();
    } catch (exc) {
      setError(exc instanceof HiveApiError ? exc.message : "Save failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function applyPreset(preset: RouterPreset): Promise<void> {
    const presetSlug = `${preset.preset_id}_${Date.now().toString(36).slice(-4)}`;
    setBusyId(preset.preset_id);
    setError(null);
    try {
      await hivePostJson("tools/super-routers/preset", {
        preset_id: preset.preset_id,
        slug: presetSlug,
        name: preset.title,
      });
      setSuccess(`Preset “${preset.title}” created (inactive — connect connectors, then activate).`);
      await load();
    } catch (exc) {
      setError(exc instanceof HiveApiError ? exc.message : "Preset setup failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function toggleRouterActive(row: SuperToolRouterRow): Promise<void> {
    setBusyId(row.id);
    try {
      await hivePatchJson(`tools/super-routers/${encodeURIComponent(row.id)}`, { is_active: !row.is_active });
      await load();
    } catch (exc) {
      setError(exc instanceof HiveApiError ? exc.message : "Toggle failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function deleteRouter(row: SuperToolRouterRow): Promise<void> {
    const ok = typeof window !== "undefined" ? window.confirm(`Delete super router “${row.name}”?`) : false;
    if (!ok) return;
    setBusyId(row.id);
    try {
      await hiveDelete(`tools/super-routers/${encodeURIComponent(row.id)}`);
      setSuccess(`Router “${row.name}” deleted.`);
      await load();
    } catch (exc) {
      setError(exc instanceof HiveApiError ? exc.message : "Delete failed.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-6">
      <V4CardHeader
        as="h3"
        title="Super Tool Routers"
        description="Stack multiple marketplace connectors per manager lane — agents inherit ordered slugs when routers are active."
        actions={
          <button type="button" className="qs-btn qs-btn--primary qs-btn--sm gap-2" onClick={openCreate}>
            <Plus className="h-4 w-4" aria-hidden />
            New router
          </button>
        }
      />

      {error ? (
        <p className="rounded-xl border border-(--qs-red)/35 bg-(--qs-red)/10 px-3 py-2 text-xs text-(--qs-red)">{error}</p>
      ) : null}
      {success ? (
        <p className="rounded-xl border border-(--qs-green)/35 bg-(--qs-green)/10 px-3 py-2 text-xs text-(--qs-green)">
          {success}
        </p>
      ) : null}

      <div className="space-y-3">
        <p className="v4-field-label">Quick setup presets</p>
        <div className="grid gap-3 md:grid-cols-3">
          {presets.map((preset) => (
            <article key={preset.preset_id} className="v4-dream-cycle-card flex flex-col gap-2">
              <div className="flex items-start gap-2">
                <Zap className="mt-0.5 h-4 w-4 shrink-0 text-pollen" aria-hidden />
                <div>
                  <p className="text-sm font-semibold text-(--qs-text)">{preset.title}</p>
                  <p className="mt-1 text-xs text-(--qs-text-3)">{preset.description}</p>
                </div>
              </div>
              <p className="font-mono text-[10px] text-(--qs-text-3)">{preset.connector_slugs.join(" → ")}</p>
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm mt-auto"
                disabled={busyId === preset.preset_id}
                onClick={() => void applyPreset(preset)}
              >
                {busyId === preset.preset_id ? "Creating…" : "Use preset"}
              </button>
            </article>
          ))}
        </div>
      </div>

      {editorOpen ? (
        <div className="space-y-4 rounded-2xl border border-pollen/30 bg-pollen/5 p-4">
          <p className="text-sm font-semibold text-(--qs-text)">{editId ? "Edit super router" : "Create super router"}</p>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="flex flex-col gap-2 text-sm font-medium text-(--qs-text-2)">
              Name
              <input className="qs-input text-sm" value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium text-(--qs-text-2)">
              Slug
              <input
                className="qs-input font-mono text-sm"
                value={slug}
                disabled={Boolean(editId)}
                onChange={(e) => setSlug(e.target.value)}
              />
            </label>
            <label className="flex flex-col gap-2 md:col-span-2 text-sm font-medium text-(--qs-text-2)">
              Description
              <textarea
                className="v4-textarea text-sm"
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </label>
            <label className="flex flex-col gap-2 md:col-span-2 text-sm font-medium text-(--qs-text-2)">
              Routing mode
              <QsSelect
                value={routingMode}
                onValueChange={(next) => setRoutingMode(next as (typeof ROUTING_MODES)[number]["value"])}
                options={ROUTING_MODES.map((row) => ({ value: row.value, label: row.label }))}
              />
            </label>
          </div>

          <div>
            <p className="v4-field-label mb-2">Manager lanes</p>
            <div className="flex flex-wrap gap-2">
              {MANAGER_LANES.map((lane) => (
                <button
                  key={lane.value}
                  type="button"
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs transition-colors",
                    managerSlugs.includes(lane.value)
                      ? "border-pollen/50 bg-pollen/15 text-pollen"
                      : "border-(--qs-border) text-(--qs-text-3) hover:border-(--qs-border-2)",
                  )}
                  onClick={() => toggleManager(lane.value)}
                >
                  {lane.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="v4-field-label mb-2">Connector stack (priority order)</p>
            <div className="flex flex-wrap gap-2">
              {connectorOptions.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={cn(
                    "rounded-full border px-3 py-1 font-mono text-[11px] transition-colors",
                    connectorSlugs.includes(opt.value)
                      ? "border-cyan-400/50 bg-cyan-400/10 text-cyan-200"
                      : "border-(--qs-border) text-(--qs-text-3) hover:border-(--qs-border-2)",
                  )}
                  onClick={() => toggleConnector(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            {connectorSlugs.length ? (
              <p className="mt-2 font-mono text-[10px] text-(--qs-text-3)">Order: {connectorSlugs.join(" → ")}</p>
            ) : null}
          </div>

          <div className="flex flex-wrap items-center gap-4 text-sm text-(--qs-text-2)">
            <label className="inline-flex items-center gap-2">
              <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
              Active for agents
            </label>
            <label className="inline-flex items-center gap-2">
              <input type="checkbox" checked={fallbackSearch} onChange={(e) => setFallbackSearch(e.target.checked)} />
              Allow Serper/Tavily fallback hint
            </label>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              disabled={busyId === "save"}
              onClick={() => void saveRouter()}
            >
              {busyId === "save" ? "Saving…" : editId ? "Save changes" : "Create router"}
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              onClick={() => {
                setEditorOpen(false);
                resetForm();
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      <div className="space-y-3">
        <p className="v4-field-label">Your routers ({routers.length})</p>
        {!routers.length ? (
          <p className="text-sm text-(--qs-text-3)">
            No super routers yet. Use a preset or create one — connect marketplace templates first, then activate.
          </p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {routers.map((row) => (
              <article key={row.id} className="v4-dream-cycle-card flex flex-col gap-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2">
                    <GitBranch className="mt-0.5 h-4 w-4 text-cyan-300" aria-hidden />
                    <div>
                      <p className="text-sm font-semibold text-(--qs-text)">{row.name}</p>
                      <p className="font-mono text-[10px] text-(--qs-text-3)">{row.slug}</p>
                    </div>
                  </div>
                  <V4Badge tone={row.is_active ? "ok" : "warn"}>{row.is_active ? "active" : "inactive"}</V4Badge>
                </div>
                {row.description ? <p className="text-xs text-(--qs-text-3)">{row.description}</p> : null}
                <p className="text-[11px] text-(--qs-text-3)">{routingLabel(row.routing_mode)}</p>
                <p className="font-mono text-[10px] text-(--qs-text-3)">{row.connector_slugs.join(" → ")}</p>
                <p className="text-[10px] text-(--qs-text-3)">Lanes: {row.manager_slugs.join(", ") || "all"}</p>
                <div className="mt-auto flex flex-wrap gap-2">
                  <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => openEdit(row)}>
                    Edit
                  </button>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    disabled={busyId === row.id}
                    onClick={() => void toggleRouterActive(row)}
                  >
                    {row.is_active ? "Pause" : "Activate"}
                  </button>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm text-(--qs-red) gap-1"
                    disabled={busyId === row.id}
                    onClick={() => void deleteRouter(row)}
                  >
                    <Trash2 className="h-3.5 w-3.5" aria-hidden />
                    Delete
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
