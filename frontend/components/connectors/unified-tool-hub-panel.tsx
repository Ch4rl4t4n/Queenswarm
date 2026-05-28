"use client";

import type { JSX } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DynamicCollectorDeck,
  type CollectorCardItem,
  type CollectorTab,
} from "@/components/hive/dynamic-collector-deck";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { V4Badge, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

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
  const registry = useMemo(() => overview?.registry ?? [], [overview?.registry]);

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

  const toolTabs: CollectorTab[] = useMemo(() => {
    const ranked = filteredRegistry.filter((row) => (row.score ?? 0) > 0);
    const lowCost = filteredRegistry.filter((row) => row.cost_tier === "low");
    const fast = filteredRegistry.filter((row) => row.latency_tier === "fast");
    return [
      { id: "all", label: "All tools", count: filteredRegistry.length, tone: "info" },
      { id: "ranked", label: "Ranked", count: ranked.length, tone: "gold" },
      { id: "low_cost", label: "Low cost", count: lowCost.length, tone: "ok" },
      { id: "fast", label: "Fast", count: fast.length, tone: "purple" },
    ];
  }, [filteredRegistry]);

  const toolItemsByTab = useMemo(() => {
    const toCard = (row: ToolRegistryRow): CollectorCardItem => ({
      id: `${row.connector_slug}:${row.tool_name}`,
      title: row.tool_name,
      body: row.description,
      meta: `${row.connector_slug} · ${row.method} ${row.path}`,
      badge:
        typeof row.score === "number" && row.score > 0
          ? `score ${row.score.toFixed(2)}`
          : row.cost_tier
            ? costLabel(row.cost_tier)
            : "tool",
      badgeTone:
        typeof row.score === "number" && row.score > 0
          ? "ok"
          : costTone(row.cost_tier ?? undefined),
      footer: (
        <div className="flex flex-wrap gap-2">
          {row.cost_tier ? <V4Badge tone={costTone(row.cost_tier)}>{costLabel(row.cost_tier)}</V4Badge> : null}
          {row.latency_tier ? (
            <V4Badge tone={latencyTone(row.latency_tier)}>{latencyLabel(row.latency_tier)}</V4Badge>
          ) : null}
          <V4Badge tone="info">{row.connector_display_name || row.connector_slug}</V4Badge>
        </div>
      ),
    });

    const ranked = filteredRegistry.filter((row) => (row.score ?? 0) > 0);
    const lowCost = filteredRegistry.filter((row) => row.cost_tier === "low");
    const fast = filteredRegistry.filter((row) => row.latency_tier === "fast");

    return {
      all: filteredRegistry.map(toCard),
      ranked: ranked.map(toCard),
      low_cost: lowCost.map(toCard),
      fast: fast.map(toCard),
    };
  }, [filteredRegistry]);

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
        hint={sectionHintNode("integrationsHubTools")}
      />

      {error ? (
        <p className="rounded-xl border border-(--qs-red)/35 bg-(--qs-red)/10 px-3 py-2 text-xs text-(--qs-red)">{error}</p>
      ) : null}

      {venice ? (
        <article className="v4-dream-cycle-card qs-bubble--tint-cyan flex flex-col gap-3">
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
                  className="qs-bubble-inner rounded-md px-2 py-0.5 font-mono text-[10px] text-(--qs-text-3)"
                >
                  {hint.name}
                </span>
              ))}
            </div>
          ) : null}
          {!venice.installed ? (
            <div className="v4-dream-cycle-card-actions">
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm"
                disabled={busyId === venice.id}
                onClick={() => void installVenice()}
              >
                {busyId === venice.id ? "Installing Venice…" : "Install Venice MCP preset"}
              </button>
            </div>
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

      <DynamicCollectorDeck
        tabs={toolTabs}
        itemsByTab={toolItemsByTab}
        defaultTabId={goal.trim() ? "ranked" : "all"}
        emptyLabel={
          overview
            ? "No tools in this collector — adjust goal filter or install a preset."
            : "Loading registry…"
        }
      />
    </div>
  );
}
