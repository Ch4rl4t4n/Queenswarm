"use client";

import type { JSX } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { V4Badge, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

type CostTier = "low" | "medium" | "high";
type LatencyTier = "fast" | "balanced" | "slow";

interface ToolRegistryRow {
  connector_slug: string;
  connector_display_name: string;
  tool_name: string;
  description: string;
  method: string;
  path: string;
  cost_tier?: CostTier | null;
  latency_tier?: LatencyTier | null;
  score?: number;
  is_active: boolean;
}

interface FeaturedPresetRow {
  source: string;
  id: string;
  slug: string;
  title: string;
  summary: string;
  category: string;
  auth_type: string;
  tool_count: number;
  installed: boolean;
  featured?: boolean;
  mcp_preset?: boolean;
  cost_tier?: CostTier | null;
  latency_tier?: LatencyTier | null;
  tool_hints?: Array<{ name: string; cost_tier?: CostTier; latency_tier?: LatencyTier }>;
}

interface ToolHubOverviewResponse {
  registry: ToolRegistryRow[];
  featured_presets: FeaturedPresetRow[];
  venice_preset: FeaturedPresetRow | null;
  totals: {
    installed_tools: number;
    active_presets: number;
    featured_count: number;
  };
  goal?: string | null;
}

function costLabel(tier: CostTier | null | undefined): string {
  if (tier === "low") return "Low cost";
  if (tier === "medium") return "Med cost";
  if (tier === "high") return "High cost";
  return "—";
}

function latencyLabel(tier: LatencyTier | null | undefined): string {
  if (tier === "fast") return "Fast";
  if (tier === "balanced") return "Balanced";
  if (tier === "slow") return "Slow";
  return "—";
}

function costTone(tier: CostTier | null | undefined): "ok" | "warn" | "err" {
  if (tier === "low") return "ok";
  if (tier === "high") return "err";
  return "warn";
}

function latencyTone(tier: LatencyTier | null | undefined): "ok" | "warn" | "err" {
  if (tier === "fast") return "ok";
  if (tier === "slow") return "err";
  return "warn";
}

export function UnifiedToolHubPanel(): JSX.Element {
  const [overview, setOverview] = useState<ToolHubOverviewResponse | null>(null);
  const [goal, setGoal] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (searchGoal?: string): Promise<void> => {
    setError(null);
    try {
      const query = searchGoal?.trim() ? `?goal=${encodeURIComponent(searchGoal.trim())}` : "";
      const payload = await hiveGet<ToolHubOverviewResponse>(`tools/hub/overview${query}`);
      setOverview(payload);
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Tool Hub unavailable.";
      setError(detail);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const venice = overview?.venice_preset ?? null;
  const registry = overview?.registry ?? [];

  const filteredRegistry = useMemo(() => {
    const needle = goal.trim().toLowerCase();
    if (!needle) return registry;
    return registry.filter(
      (row) =>
        row.tool_name.toLowerCase().includes(needle) ||
        row.connector_slug.toLowerCase().includes(needle) ||
        row.description.toLowerCase().includes(needle),
    );
  }, [goal, registry]);

  async function installVenice(): Promise<void> {
    if (!venice) return;
    setBusyId(venice.id);
    setError(null);
    try {
      await hivePostJson("tools/marketplace/install", {
        source: venice.source || "phase3_template",
        entry_id: venice.id,
      });
      await load(goal);
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Venice install failed.";
      setError(detail);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-6">
      <V4CardHeader
        as="h3"
        title="Unified Tool Hub"
        description="Orchestrated MCP registry with cost and latency hints — supervisor lanes pick tools by goal overlap."
      />

      {error ? (
        <p className="rounded-xl border border-(--qs-red)/35 bg-(--qs-red)/10 px-3 py-2 text-xs text-(--qs-red)">{error}</p>
      ) : null}

      {venice ? (
        <article className="v4-dream-cycle-card space-y-3 border border-(--qs-cyan)/25 bg-(--qs-cyan)/5">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-(--qs-cyan)">Featured MCP preset</p>
              <p className="text-sm font-semibold text-(--qs-text)">{venice.title}</p>
            </div>
            <V4Badge tone={venice.installed ? "ok" : "warn"}>{venice.installed ? "installed" : "not installed"}</V4Badge>
          </div>
          <p className="text-xs text-(--qs-text-3)">{venice.summary}</p>
          <div className="flex flex-wrap gap-2">
            {venice.cost_tier ? <V4Badge tone={costTone(venice.cost_tier)}>{costLabel(venice.cost_tier)}</V4Badge> : null}
            {venice.latency_tier ? (
              <V4Badge tone={latencyTone(venice.latency_tier)}>{latencyLabel(venice.latency_tier)}</V4Badge>
            ) : null}
            <V4Badge tone="info">{venice.tool_count} tools</V4Badge>
          </div>
          {venice.tool_hints?.length ? (
            <div className="flex flex-wrap gap-1.5">
              {venice.tool_hints.slice(0, 6).map((hint) => (
                <span
                  key={hint.name}
                  className="rounded-md border border-(--qs-border)/60 px-2 py-0.5 font-mono text-[10px] text-(--qs-text-3)"
                >
                  {hint.name}
                </span>
              ))}
            </div>
          ) : null}
          {!venice.installed ? (
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              disabled={busyId === venice.id}
              onClick={() => void installVenice()}
            >
              {busyId === venice.id ? "Installing Venice…" : "Install Venice MCP preset"}
            </button>
          ) : (
            <p className="text-[11px] text-(--qs-green)">Venice connector ready — add bearer token in hub and test connection.</p>
          )}
        </article>
      ) : null}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="flex flex-1 flex-col gap-1">
          <span className="v4-field-label">Goal filter</span>
          <input
            type="search"
            className="qs-input"
            placeholder="e.g. search knowledge, generate image, TTS briefing"
            value={goal}
            onChange={(event) => setGoal(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void load(goal);
            }}
          />
        </label>
        <button type="button" className="qs-btn qs-btn--secondary qs-btn--sm" onClick={() => void load(goal)}>
          Rank by goal
        </button>
      </div>

      {overview ? (
        <p className="font-mono text-[11px] text-(--qs-text-3)">
          {overview.totals.installed_tools} active tools · {overview.totals.active_presets} installed presets
        </p>
      ) : null}

      <div className="overflow-x-auto rounded-xl border border-(--qs-border)/50">
        <table className="min-w-full text-left text-xs">
          <thead className="border-b border-(--qs-border)/50 bg-(--qs-surface-2)/40">
            <tr>
              <th className="px-3 py-2 font-medium text-(--qs-text-2)">Tool</th>
              <th className="px-3 py-2 font-medium text-(--qs-text-2)">Connector</th>
              <th className="px-3 py-2 font-medium text-(--qs-text-2)">Cost</th>
              <th className="px-3 py-2 font-medium text-(--qs-text-2)">Speed</th>
              <th className="px-3 py-2 font-medium text-(--qs-text-2)">Score</th>
            </tr>
          </thead>
          <tbody>
            {filteredRegistry.map((row) => (
              <tr key={`${row.connector_slug}:${row.tool_name}`} className="border-b border-(--qs-border)/30 last:border-0">
                <td className="px-3 py-2">
                  <p className="font-mono text-[11px] text-(--qs-text)">{row.tool_name}</p>
                  <p className="text-[10px] text-(--qs-text-3)">{row.description}</p>
                </td>
                <td className="px-3 py-2 font-mono text-[11px] text-(--qs-text-3)">{row.connector_slug}</td>
                <td className="px-3 py-2">
                  {row.cost_tier ? (
                    <V4Badge tone={costTone(row.cost_tier)}>{costLabel(row.cost_tier)}</V4Badge>
                  ) : (
                    <span className="text-(--qs-text-3)">—</span>
                  )}
                </td>
                <td className="px-3 py-2">
                  {row.latency_tier ? (
                    <V4Badge tone={latencyTone(row.latency_tier)}>{latencyLabel(row.latency_tier)}</V4Badge>
                  ) : (
                    <span className="text-(--qs-text-3)">—</span>
                  )}
                </td>
                <td className={cn("px-3 py-2 font-mono text-[11px]", row.score && row.score > 0 ? "text-(--qs-green)" : "text-(--qs-text-3)")}>
                  {typeof row.score === "number" ? row.score.toFixed(2) : "—"}
                </td>
              </tr>
            ))}
            {!filteredRegistry.length ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-sm text-(--qs-text-3)">
                  {overview ? "No tools match — install a marketplace preset or provision a connector." : "Loading registry…"}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
