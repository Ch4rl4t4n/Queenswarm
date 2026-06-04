"use client";

import Link from "next/link";
import { DownloadIcon, Loader2Icon, PlayIcon, SparklesIcon, StoreIcon, XIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { ContentPackFactoryManualPanel } from "@/components/apps-tools/content-pack-factory-manual-panel";
import {
  FactoryLlmReadinessBanner,
  factoryBuildDisabled,
  type FactoryLlmReadiness,
} from "@/components/apps-tools/factory-llm-readiness-banner";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { InfoHint } from "@/components/hive/info-hint";
import { HiveSwitch } from "@/components/ui/hive-switch";
import { V4Badge, V4Card, V4CardHeader, V4Chip } from "@/components/ui/v4";
import { downloadContentPackExportBundle, type ContentPackExportResponse } from "@/lib/content-pack-export-utils";
import { HiveApiError, hiveGet, hivePostJson, hivePutJson } from "@/lib/api";
import { MANUAL_HREFS } from "@/lib/manual-routes";
import { supervisorSessionAgentsHref } from "@/lib/supervisor-session";
import type { ContentPackFactoryTab } from "@/lib/apps-tools-routes";

interface ContentPackFactoryPolicy {
  enabled: boolean;
  niche_seeds: string[];
  auto_build_enabled: boolean;
  auto_build_min_score: number;
  max_builds_per_week: number;
  research_cron_enabled: boolean;
}

interface ContentPackOpportunityRow {
  id: string;
  niche: string;
  title: string;
  rationale: string;
  demand_score: number;
  competition_score: number;
  buildability_score: number;
  composite_score: number;
  suggested_price_eur_cents: number;
  status: string;
  supervisor_session_id: string | null;
  supervisor_session_status: string | null;
  forge_suggestion_id: string | null;
  tenant_content_pack_id: string | null;
}

interface TenantContentPackRow {
  id: string;
  slug: string;
  title: string;
  description: string;
  channel: string;
  source: string;
  verified_at: string | null;
  github_exported_at: string | null;
  gumroad_product_id: string | null;
  gumroad_product_url: string | null;
  gumroad_published: boolean | null;
  snippet_count: number;
}

interface ContentPackFactorySnapshot {
  policy: ContentPackFactoryPolicy;
  opportunities: ContentPackOpportunityRow[];
  library: TenantContentPackRow[];
  queue_count: number;
  building_count: number;
  research_keys_configured: boolean;
  export_ready: boolean;
  gumroad_listing_ready: boolean;
  gumroad_publish_ready: boolean;
  llm: FactoryLlmReadiness | null;
}

const FALLBACK_PACK_PRESETS: string[] = [
  "30-day Instagram content calendar for coaches",
  "LinkedIn thought-leadership pack for B2B SaaS",
  "TikTok hook library for e-commerce brands",
  "Newsletter launch sequence for indie hackers",
  "Twitter/X thread pack for crypto analysts",
];

function scorePct(score: number): string {
  return `${Math.round(score * 100)}%`;
}

function priceEur(cents: number): string {
  return `€${(cents / 100).toFixed(2)}`;
}

function opportunityStatusLabel(row: ContentPackOpportunityRow): string {
  if (row.status === "building") return "Building…";
  if (row.status === "awaiting_forge") return "Session done — approve forge";
  if (row.status === "completed") return "Completed";
  if (row.status === "failed") return "Build failed";
  return row.status;
}

interface ContentPackFactoryPanelProps {
  activeTab: ContentPackFactoryTab;
  refreshToken?: number;
  onError?: (message: string | null) => void;
  onQueueCountChange?: (count: number | undefined) => void;
}

export function ContentPackFactoryPanel({
  activeTab,
  refreshToken = 0,
  onError,
  onQueueCountChange,
}: ContentPackFactoryPanelProps): JSX.Element {
  const [snapshot, setSnapshot] = useState<ContentPackFactorySnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [researchBusy, setResearchBusy] = useState(false);
  const [policyDraft, setPolicyDraft] = useState<ContentPackFactoryPolicy | null>(null);
  const [nicheInput, setNicheInput] = useState("");
  const [verticalSeeds, setVerticalSeeds] = useState<string[]>(FALLBACK_PACK_PRESETS);
  const [starterSeeds, setStarterSeeds] = useState<string[]>(FALLBACK_PACK_PRESETS);

  const loadSnapshot = useCallback(async () => {
    setLoading(true);
    onError?.(null);
    try {
      const data = await hiveGet<ContentPackFactorySnapshot>("/content-pack-factory/snapshot");
      setSnapshot(data);
      setPolicyDraft(data.policy);
    } catch (err) {
      const message = err instanceof HiveApiError ? err.message : "Failed to load Content Pack Factory.";
      onError?.(message);
    } finally {
      setLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    void loadSnapshot();
  }, [loadSnapshot, refreshToken]);

  useEffect(() => {
    if (!snapshot) {
      onQueueCountChange?.(undefined);
      return;
    }
    const count = snapshot.queue_count + snapshot.building_count;
    onQueueCountChange?.(count > 0 ? count : undefined);
  }, [onQueueCountChange, snapshot]);

  useEffect(() => {
    void hiveGet<{ vertical: string[]; starter: string[] }>("/content-pack-factory/vertical-seeds")
      .then((data) => {
        if (data.vertical?.length) setVerticalSeeds(data.vertical);
        if (data.starter?.length) setStarterSeeds(data.starter);
      })
      .catch(() => {
        /* fallback presets */
      });
  }, []);

  const runResearch = async () => {
    setResearchBusy(true);
    try {
      const result = await hivePostJson<{ created: number; builds_started: number }>(
        "/content-pack-factory/research/run",
        {},
      );
      toast.success(`Research: ${result.created} new · ${result.builds_started} builds started`);
      await loadSnapshot();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Research failed");
    } finally {
      setResearchBusy(false);
    }
  };

  const startBuild = async (opportunityId: string) => {
    setBusyId(opportunityId);
    try {
      const result = await hivePostJson<{ session_id: string }>(
        `/content-pack-factory/opportunities/${opportunityId}/build`,
        {},
      );
      toast.success("Build started");
      if (result.session_id) {
        window.open(supervisorSessionAgentsHref(result.session_id), "_blank", "noopener,noreferrer");
      }
      await loadSnapshot();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Build failed");
    } finally {
      setBusyId(null);
    }
  };

  const dismissOpportunity = async (opportunityId: string) => {
    setBusyId(opportunityId);
    try {
      await hivePostJson(`/content-pack-factory/opportunities/${opportunityId}/dismiss`, {});
      await loadSnapshot();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Dismiss failed");
    } finally {
      setBusyId(null);
    }
  };

  const exportPack = async (packId: string) => {
    setBusyId(packId);
    try {
      const bundle = await hivePostJson<ContentPackExportResponse>(`/content-pack-factory/packs/${packId}/export`, {});
      await downloadContentPackExportBundle(bundle);
      toast.success("Export downloaded");
      await loadSnapshot();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Export failed");
    } finally {
      setBusyId(null);
    }
  };

  const createGumroadDraft = async (packId: string) => {
    setBusyId(packId);
    try {
      const res = await hivePostJson<{ product_url: string | null }>(
        `/content-pack-factory/packs/${packId}/export/gumroad-draft`,
        {},
      );
      toast.success("Gumroad draft created.", { description: res.product_url ?? "Finish in Gumroad UI." });
      await loadSnapshot();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Gumroad draft failed");
    } finally {
      setBusyId(null);
    }
  };

  const publishGumroadListing = async (packId: string, createIfMissing: boolean) => {
    setBusyId(packId);
    try {
      const res = await hivePostJson<{ short_url: string; published: boolean }>(
        `/content-pack-factory/packs/${packId}/export/gumroad-publish`,
        { create_if_missing: createIfMissing },
      );
      toast.success("Gumroad listing published.", { description: res.short_url || "Product is live." });
      await loadSnapshot();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Gumroad publish failed");
    } finally {
      setBusyId(null);
    }
  };

  const savePolicy = async () => {
    if (!policyDraft) return;
    setBusyId("policy");
    try {
      const saved = await hivePutJson<ContentPackFactoryPolicy>("/content-pack-factory/policy", policyDraft);
      setPolicyDraft(saved);
      setSnapshot((prev) => (prev ? { ...prev, policy: saved } : prev));
      toast.success("Policy saved");
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Save failed");
    } finally {
      setBusyId(null);
    }
  };

  const addNicheSeed = () => {
    const seed = nicheInput.trim();
    if (!seed || !policyDraft) return;
    if (policyDraft.niche_seeds.includes(seed)) return;
    setPolicyDraft({ ...policyDraft, niche_seeds: [...policyDraft.niche_seeds, seed].slice(0, 12) });
    setNicheInput("");
  };

  const opportunities = snapshot?.opportunities ?? [];
  const library = snapshot?.library ?? [];
  const researchRows = useMemo(
    () => opportunities.filter((row) => row.status === "pending"),
    [opportunities],
  );
  const queueRows = useMemo(
    () =>
      opportunities.filter((row) =>
        ["queued", "building", "awaiting_forge", "failed"].includes(row.status),
      ),
    [opportunities],
  );
  const failedCount = opportunities.filter((row) => row.status === "failed").length;
  const buildBlocked = factoryBuildDisabled(snapshot?.llm);

  if (loading && !snapshot) {
    return (
      <div className="qs-bubble flex min-h-[12rem] items-center justify-center gap-2 p-6 text-sm text-white/60">
        <Loader2Icon className="size-4 animate-spin" aria-hidden />
        Loading Content Pack Factory…
      </div>
    );
  }

  const renderOpportunityRow = (row: ContentPackOpportunityRow) => (
    <div key={row.id} className="qs-bubble flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-white">{row.title}</span>
          <V4Badge tone="info">{opportunityStatusLabel(row)}</V4Badge>
          <V4Badge tone="gold">{scorePct(row.composite_score)}</V4Badge>
          <V4Badge tone="info">{priceEur(row.suggested_price_eur_cents)}</V4Badge>
        </div>
        <p className="mt-1 text-xs text-white/50 line-clamp-2">{row.rationale}</p>
      </div>
      <div className="flex shrink-0 flex-wrap gap-2">
        {row.forge_suggestion_id ? (
          <Link href={`/agents?forge=${row.forge_suggestion_id}`} className="qs-btn qs-btn--primary qs-btn--sm">
            Review forge
          </Link>
        ) : null}
        {row.supervisor_session_id && row.status === "building" ? (
          <Link
            href={supervisorSessionAgentsHref(row.supervisor_session_id)}
            className="qs-btn qs-btn--ghost qs-btn--sm"
          >
            Open session
          </Link>
        ) : null}
        {row.status === "pending" || row.status === "queued" ? (
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm"
            disabled={busyId === row.id || buildBlocked}
            title={buildBlocked ? snapshot?.llm?.recommended_action : undefined}
            onClick={() => void startBuild(row.id)}
          >
            {busyId === row.id ? <Loader2Icon className="size-3.5 animate-spin" /> : <PlayIcon className="size-3.5" />}
            Build
          </button>
        ) : null}
        {row.status !== "completed" && row.status !== "dismissed" ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm"
            disabled={busyId === row.id}
            onClick={() => void dismissOpportunity(row.id)}
            aria-label="Dismiss"
          >
            <XIcon className="size-3.5" />
          </button>
        ) : null}
      </div>
    </div>
  );

  return (
    <div id="pack-factory" className="flex flex-col gap-4 scroll-mt-24">
      {activeTab === "guide" ? <ContentPackFactoryManualPanel /> : null}

      {activeTab === "research" || activeTab === "queue" ? (
        <FactoryLlmReadinessBanner
          llm={snapshot?.llm}
          onSmoked={(next) => setSnapshot((prev) => (prev ? { ...prev, llm: next } : prev))}
        />
      ) : null}

      {activeTab === "research" ? (
        <>
          <V4Card>
            <V4CardHeader
              title="Factory status"
              description="Queue snapshot and research controls."
              hint={sectionHintNode("contentPackFactoryResearch")}
              actions={
                <button
                  type="button"
                  className="qs-btn qs-btn--primary qs-btn--sm"
                  disabled={researchBusy}
                  onClick={() => void runResearch()}
                >
                  {researchBusy ? <Loader2Icon className="size-3.5 animate-spin" /> : <SparklesIcon className="size-3.5" />}
                  Run research
                </button>
              }
            />
            <div className="space-y-3 px-4 pb-4 text-sm text-white/70">
              <div className="flex flex-wrap gap-2">
                <V4Chip>Queue {snapshot?.queue_count ?? 0}</V4Chip>
                <V4Chip>Building {snapshot?.building_count ?? 0}</V4Chip>
                <V4Chip>Research keys {snapshot?.research_keys_configured ? "OK" : "optional"}</V4Chip>
                {failedCount > 0 ? <V4Badge tone="warn">{failedCount} failed</V4Badge> : null}
              </div>
              <p className="flex flex-wrap items-center gap-1 text-xs text-white/50">
                Builds use Grok (xAI) as primary — run smoke test before Build.
                <InfoHint
                  title="Grok required"
                  description="Skill/Content Pack Factory uses your Grok API key. Claude and OpenAI are optional fallbacks only."
                  options={[
                    "Settings → AI · LLM keys — Grok must show vault + CONNECTED",
                    "Run smoke test in Skill Factory or Pack Factory",
                  ]}
                  manualHref="/manual#content-pack-factory"
                  className="hive-inline-hint"
                />
              </p>
            </div>
          </V4Card>

          <V4Card>
            <V4CardHeader
              title="Market opportunities"
              description="Ranked niches ready for factory builds."
              hint={sectionHintNode("contentPackFactoryQueue")}
            />
            <div className="space-y-2 px-4 pb-4">
              {researchRows.length === 0 ? (
                <p className="text-sm text-white/50">No pending niches — run research or add niche seeds in Settings.</p>
              ) : (
                researchRows.map((row) => renderOpportunityRow(row))
              )}
            </div>
          </V4Card>
        </>
      ) : null}

      {activeTab === "queue" ? (
        <V4Card>
          <V4CardHeader
            title="Build queue"
            description="Active builds, forge review, and failed runs."
            hint={sectionHintNode("contentPackFactoryQueue")}
          />
          <div className="space-y-2 px-4 pb-4">
            {queueRows.length === 0 ? (
              <p className="text-sm text-white/50">Nothing in queue — start from Research tab.</p>
            ) : (
              queueRows.map((row) => renderOpportunityRow(row))
            )}
          </div>
        </V4Card>
      ) : null}

      {activeTab === "library" ? (
        <V4Card>
          <V4CardHeader
            title="Library"
            description="Verified packs — export bundles for Gumroad."
            hint={sectionHintNode("contentPackFactoryLibrary")}
          />
          <div className="space-y-2 px-4 pb-4">
          {library.length === 0 ? (
            <p className="text-sm text-white/50">No packs yet. Complete a build and approve the forge proposal.</p>
          ) : (
            library.map((pack) => (
              <div key={pack.id} className="qs-bubble flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-white">{pack.title}</span>
                    <V4Badge tone="info">{pack.channel}</V4Badge>
                    <V4Badge tone="ok">{pack.snippet_count} snippets</V4Badge>
                    {pack.verified_at ? <V4Badge tone="gold">Verified</V4Badge> : null}
                  </div>
                  <p className="mt-1 text-xs text-white/50">{pack.slug}</p>
                </div>
                <div className="flex shrink-0 flex-wrap gap-2">
                  <button
                    type="button"
                    className="qs-btn qs-btn--primary qs-btn--sm"
                    disabled={busyId === pack.id}
                    onClick={() => void exportPack(pack.id)}
                  >
                    {busyId === pack.id ? (
                      <Loader2Icon className="size-3.5 animate-spin" />
                    ) : (
                      <DownloadIcon className="size-3.5" />
                    )}
                    Export
                  </button>
                  {snapshot?.gumroad_listing_ready ? (
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm"
                      disabled={busyId === pack.id}
                      onClick={() => void createGumroadDraft(pack.id)}
                    >
                      <StoreIcon className="size-3.5" />
                      Gumroad draft
                    </button>
                  ) : null}
                  {snapshot?.gumroad_publish_ready ? (
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm"
                      disabled={busyId === pack.id || pack.gumroad_published === true}
                      onClick={() => void publishGumroadListing(pack.id, !pack.gumroad_product_id)}
                    >
                      {pack.gumroad_published ? "Published" : "Gumroad publish"}
                    </button>
                  ) : null}
                  {pack.gumroad_product_url ? (
                    <Link href={pack.gumroad_product_url} className="qs-btn qs-btn--ghost qs-btn--sm" target="_blank" rel="noopener noreferrer">
                      Open Gumroad
                    </Link>
                  ) : null}
                </div>
              </div>
            ))
          )}
        </div>
        </V4Card>
      ) : null}

      {activeTab === "settings" && policyDraft ? (
        <V4Card>
          <V4CardHeader
            title="Automation policy"
            description="Niche seeds and optional auto-build."
            hint={sectionHintNode("contentPackFactorySettings")}
          />
          <div className="space-y-3 px-4 pb-4 text-sm">
            <label className="flex items-center gap-2">
              <HiveSwitch
                checked={policyDraft.auto_build_enabled}
                onCheckedChange={(checked) => setPolicyDraft({ ...policyDraft, auto_build_enabled: checked })}
              />
              Auto-build top opportunities after research
              <InfoHint
                title="Auto-build"
                description="When ON, research may start builds for scores ≥ threshold. Keep OFF until LLM smoke passes."
                options={["Start OFF for first pack", "Requires factory_llm_readiness.py --smoke PASS"]}
                manualHref="/manual#content-pack-factory"
                className="hive-inline-hint"
              />
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm"
                onClick={() =>
                  setPolicyDraft({
                    ...policyDraft,
                    niche_seeds: starterSeeds.slice(0, 8),
                  })
                }
              >
                Apply vertical starter
              </button>
              {verticalSeeds.slice(0, 6).map((preset) => (
                <button
                  key={preset}
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--xs"
                  onClick={() =>
                    setPolicyDraft({
                      ...policyDraft,
                      niche_seeds: [...new Set([...policyDraft.niche_seeds, preset])].slice(0, 12),
                    })
                  }
                >
                  + {preset.slice(0, 36)}…
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                className="qs-input flex-1"
                placeholder="Custom niche seed"
                value={nicheInput}
                onChange={(e) => setNicheInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") addNicheSeed();
                }}
              />
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={addNicheSeed}>
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {policyDraft.niche_seeds.map((seed) => (
                <V4Chip key={seed}>
                  {seed}
                  <button
                    type="button"
                    className="ml-1 opacity-60 hover:opacity-100"
                    onClick={() =>
                      setPolicyDraft({
                        ...policyDraft,
                        niche_seeds: policyDraft.niche_seeds.filter((s) => s !== seed),
                      })
                    }
                    aria-label={`Remove ${seed}`}
                  >
                    ×
                  </button>
                </V4Chip>
              ))}
            </div>
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              disabled={busyId === "policy"}
              onClick={() => void savePolicy()}
            >
              Save policy
            </button>
          </div>
        </V4Card>
      ) : null}
    </div>
  );
}
