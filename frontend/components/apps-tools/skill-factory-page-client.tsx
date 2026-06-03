"use client";

import Link from "next/link";
import { DownloadIcon, Loader2Icon, PlayIcon, RefreshCwIcon, SparklesIcon, XIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { SkillFactoryManualPanel } from "@/components/apps-tools/skill-factory-manual-panel";
import { HiveSwitch } from "@/components/ui/hive-switch";
import { V4Badge, V4Card, V4CardHeader, V4Chip } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson, hivePutJson } from "@/lib/api";
import { downloadSkillExportBundle } from "@/lib/skill-export-utils";
import type { SkillExportResponse } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type FactoryTab = "guide" | "research" | "queue" | "library" | "settings";

interface SkillFactoryPolicy {
  enabled: boolean;
  niche_seeds: string[];
  auto_build_enabled: boolean;
  auto_build_min_score: number;
  max_builds_per_week: number;
  research_cron_enabled: boolean;
}

interface SkillOpportunityRow {
  id: string;
  niche: string;
  title: string;
  rationale: string;
  composite_score: number;
  suggested_price_eur_cents: number;
  status: string;
  supervisor_session_id: string | null;
  tenant_skill_id: string | null;
}

interface TenantSkillRow {
  id: string;
  slug: string;
  title: string;
  description: string;
  source: string;
  verified_at: string | null;
  github_exported_at: string | null;
  keywords: string[];
}

interface SkillFactorySnapshot {
  policy: SkillFactoryPolicy;
  opportunities: SkillOpportunityRow[];
  library: TenantSkillRow[];
  queue_count: number;
  building_count: number;
}

const TABS: { id: FactoryTab; label: string }[] = [
  { id: "guide", label: "Guide" },
  { id: "research", label: "Research" },
  { id: "queue", label: "Queue" },
  { id: "library", label: "Library" },
  { id: "settings", label: "Settings" },
];

function scorePct(score: number): string {
  return `${Math.round(score * 100)}%`;
}

function priceEur(cents: number): string {
  return `€${(cents / 100).toFixed(2)}`;
}

export function SkillFactoryPageClient(): JSX.Element {
  const [tab, setTab] = useState<FactoryTab>("guide");
  const [snapshot, setSnapshot] = useState<SkillFactorySnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [researchBusy, setResearchBusy] = useState(false);
  const [policyDraft, setPolicyDraft] = useState<SkillFactoryPolicy | null>(null);
  const [nicheInput, setNicheInput] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<SkillFactorySnapshot>("skill-factory/snapshot");
      setSnapshot(data);
      setPolicyDraft(data.policy);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Skill Factory unavailable.");
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const researchRows = useMemo(
    () => (snapshot?.opportunities ?? []).filter((row) => row.status === "pending"),
    [snapshot?.opportunities],
  );
  const queueRows = useMemo(
    () =>
      (snapshot?.opportunities ?? []).filter((row) =>
        ["queued", "building"].includes(row.status),
      ),
    [snapshot?.opportunities],
  );
  const doneRows = useMemo(
    () => (snapshot?.opportunities ?? []).filter((row) => row.status === "completed"),
    [snapshot?.opportunities],
  );

  const runResearch = async (): Promise<void> => {
    setResearchBusy(true);
    try {
      const res = await hivePostJson<{ created: number; builds_started: number }>(
        "skill-factory/research/run",
        {},
      );
      toast.success(`Research done — ${res.created} new, ${res.builds_started} builds started.`);
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Research failed.");
    } finally {
      setResearchBusy(false);
    }
  };

  const buildOpportunity = async (id: string): Promise<void> => {
    setBusyId(id);
    try {
      const res = await hivePostJson<{ session_id: string }>(`skill-factory/opportunities/${id}/build`, {});
      toast.success("Factory build started.", { description: `Session ${res.session_id.slice(0, 8)}…` });
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Build failed.");
    } finally {
      setBusyId(null);
    }
  };

  const dismissOpportunity = async (id: string): Promise<void> => {
    setBusyId(id);
    try {
      await hivePostJson(`skill-factory/opportunities/${id}/dismiss`, {});
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Dismiss failed.");
    } finally {
      setBusyId(null);
    }
  };

  const exportSkill = async (id: string): Promise<void> => {
    setBusyId(id);
    try {
      const bundle = await hivePostJson<SkillExportResponse>(`skill-factory/skills/${id}/export`, {});
      await downloadSkillExportBundle(bundle);
      toast.success("GitHub pack downloaded.");
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Export failed.");
    } finally {
      setBusyId(null);
    }
  };

  const savePolicy = async (): Promise<void> => {
    if (!policyDraft) return;
    setBusyId("policy");
    try {
      await hivePutJson("skill-factory/policy", policyDraft);
      toast.success("Policy saved.");
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Save failed.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <HivePageShell
      title="Skill Factory"
      subtitle="Research → build → export GitHub-ready skills. No in-app marketplace — sell externally."
      hintKey="skillFactory"
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/manual#skill-factory" className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5">
            Manual
          </Link>
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-2" onClick={() => void load()}>
            <RefreshCwIcon className="size-4" aria-hidden />
            Refresh
          </button>
          <Link href="/agents#sessions" className="qs-btn qs-btn--ghost qs-btn--sm">
            Sessions
          </Link>
        </div>
      }
    >
      <div className="flex flex-wrap gap-2 border-b border-white/10 pb-3">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition",
              tab === item.id
                ? "border-pollen/50 bg-pollen/10 text-pollen"
                : "border-white/15 text-(--qs-text-3) hover:border-white/30",
            )}
            onClick={() => setTab(item.id)}
          >
            {item.label}
            {item.id === "queue" && snapshot ? (
              <span className="ml-1 text-pollen">({snapshot.queue_count + snapshot.building_count})</span>
            ) : null}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="mt-6 flex items-center gap-2 text-sm text-(--qs-muted)">
          <Loader2Icon className="size-4 animate-spin" aria-hidden />
          Loading Skill Factory…
        </p>
      ) : !snapshot ? (
        <V4Card className="mt-4">
          <p className="text-sm text-(--qs-text-3)">Skill Factory is disabled or unavailable.</p>
        </V4Card>
      ) : (
        <>
          {tab === "guide" ? <SkillFactoryManualPanel /> : null}

          {tab === "research" ? (
            <V4Card className="mt-4">
              <V4CardHeader
                kicker="Research lane"
                title="Market opportunities"
                description="HiveMind + niche seeds → ranked skills to build. Runs weekly via cron (Mon)."
                hint={sectionHintNode("skillFactoryResearch")}
              />
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="qs-btn qs-btn--primary qs-btn--sm gap-2"
                  disabled={researchBusy}
                  onClick={() => void runResearch()}
                >
                  {researchBusy ? (
                    <Loader2Icon className="size-4 animate-spin" aria-hidden />
                  ) : (
                    <SparklesIcon className="size-4" aria-hidden />
                  )}
                  Run research now
                </button>
                <V4Badge tone="info">{researchRows.length} pending</V4Badge>
              </div>
              <ul className="mt-4 space-y-2">
                {researchRows.map((row) => (
                  <li
                    key={row.id}
                    className="rounded-xl border border-white/10 bg-black/25 px-3 py-3 text-sm"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="font-medium text-(--qs-text)">{row.title}</p>
                        <p className="mt-1 text-xs text-(--qs-text-3)">{row.rationale}</p>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        <V4Chip>{scorePct(row.composite_score)}</V4Chip>
                        <V4Chip>{priceEur(row.suggested_price_eur_cents)}</V4Chip>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="qs-btn qs-btn--primary qs-btn--sm gap-1"
                        disabled={busyId === row.id}
                        onClick={() => void buildOpportunity(row.id)}
                      >
                        <PlayIcon className="size-3.5" aria-hidden />
                        Build skill
                      </button>
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--sm"
                        disabled={busyId === row.id}
                        onClick={() => void dismissOpportunity(row.id)}
                      >
                        <XIcon className="size-3.5" aria-hidden />
                        Dismiss
                      </button>
                    </div>
                  </li>
                ))}
                {researchRows.length === 0 ? (
                  <p className="text-xs text-(--qs-text-4)">No pending opportunities — run research.</p>
                ) : null}
              </ul>
            </V4Card>
          ) : null}

          {tab === "queue" ? (
            <V4Card className="mt-4">
              <V4CardHeader
                title="Build queue"
                description="Queued and in-progress factory runs."
                hint={sectionHintNode("skillFactoryQueue")}
              />
              <ul className="mt-4 space-y-2">
                {queueRows.map((row) => (
                  <li key={row.id} className="rounded-xl border border-cyan/25 bg-cyan/5 px-3 py-3 text-sm">
                    <p className="font-medium">{row.title}</p>
                    <p className="mt-1 text-xs text-(--qs-text-3)">Status: {row.status}</p>
                    {row.supervisor_session_id ? (
                      <Link
                        href={`/agents#sessions`}
                        className="mt-2 inline-block text-xs text-cyan underline"
                      >
                        Open Sessions → {row.supervisor_session_id.slice(0, 8)}…
                      </Link>
                    ) : null}
                  </li>
                ))}
                {queueRows.length === 0 ? (
                  <p className="text-xs text-(--qs-text-4)">Queue empty.</p>
                ) : null}
              </ul>
              {doneRows.length > 0 ? (
                <p className="mt-4 text-xs text-(--qs-text-3)">{doneRows.length} completed — see Library tab.</p>
              ) : null}
            </V4Card>
          ) : null}

          {tab === "library" ? (
            <V4Card className="mt-4">
              <V4CardHeader
                title="Tenant skill library"
                description="Active skills available to all sessions via SkillLibrary overlay."
                hint={sectionHintNode("skillFactoryLibrary")}
              />
              <ul className="mt-4 space-y-2">
                {(snapshot.library ?? []).map((row) => (
                  <li key={row.id} className="rounded-xl border border-pollen/25 bg-pollen/5 px-3 py-3 text-sm">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="font-medium">{row.title}</p>
                        <p className="mt-1 font-mono text-[10px] text-pollen">{row.slug}</p>
                        {row.description ? (
                          <p className="mt-1 text-xs text-(--qs-text-3)">{row.description.slice(0, 200)}</p>
                        ) : null}
                      </div>
                      <V4Badge tone={row.github_exported_at ? "ok" : "info"}>
                        {row.github_exported_at ? "exported" : "ready"}
                      </V4Badge>
                    </div>
                    <button
                      type="button"
                      className="qs-btn qs-btn--primary qs-btn--sm mt-3 gap-1"
                      disabled={busyId === row.id}
                      onClick={() => void exportSkill(row.id)}
                    >
                      <DownloadIcon className="size-3.5" aria-hidden />
                      Download GitHub pack
                    </button>
                  </li>
                ))}
                {snapshot.library.length === 0 ? (
                  <p className="text-xs text-(--qs-text-4)">
                    No tenant skills yet — build from Research tab, then approve forge in Agents → Suggestions.
                  </p>
                ) : null}
              </ul>
            </V4Card>
          ) : null}

          {tab === "settings" && policyDraft ? (
            <V4Card className="mt-4 space-y-4">
              <V4CardHeader
                title="Automation"
                description="Minimal operator input — research cron + optional auto-build."
                hint={sectionHintNode("skillFactorySettings")}
              />
              <label className="flex items-center justify-between gap-3 text-sm">
                <span>Factory enabled</span>
                <HiveSwitch checked={policyDraft.enabled} onCheckedChange={(v) => setPolicyDraft({ ...policyDraft, enabled: v })} />
              </label>
              <label className="flex items-center justify-between gap-3 text-sm">
                <span>Auto-build when score ≥ threshold</span>
                <HiveSwitch
                  checked={policyDraft.auto_build_enabled}
                  onCheckedChange={(v) => setPolicyDraft({ ...policyDraft, auto_build_enabled: v })}
                />
              </label>
              <label className="block text-sm">
                <span className="text-(--qs-text-3)">Auto-build min score (0–1)</span>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.01}
                  className="qs-input mt-1 w-full max-w-xs"
                  value={policyDraft.auto_build_min_score}
                  onChange={(e) =>
                    setPolicyDraft({
                      ...policyDraft,
                      auto_build_min_score: Number.parseFloat(e.target.value) || 0.72,
                    })
                  }
                />
              </label>
              <label className="block text-sm">
                <span className="text-(--qs-text-3)">Max builds per week</span>
                <input
                  type="number"
                  min={1}
                  max={10}
                  className="qs-input mt-1 w-full max-w-xs"
                  value={policyDraft.max_builds_per_week}
                  onChange={(e) =>
                    setPolicyDraft({
                      ...policyDraft,
                      max_builds_per_week: Number.parseInt(e.target.value, 10) || 3,
                    })
                  }
                />
              </label>
              <label className="block text-sm">
                <span className="text-(--qs-text-3)">Add niche seed</span>
                <div className="mt-1 flex flex-wrap gap-2">
                  <input
                    className="qs-input min-w-[12rem] flex-1"
                    placeholder="e.g. newsletter growth automation"
                    value={nicheInput}
                    onChange={(e) => setNicheInput(e.target.value)}
                  />
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    onClick={() => {
                      const next = nicheInput.trim();
                      if (!next) return;
                      setPolicyDraft({
                        ...policyDraft,
                        niche_seeds: [...policyDraft.niche_seeds, next].slice(0, 12),
                      });
                      setNicheInput("");
                    }}
                  >
                    Add
                  </button>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {policyDraft.niche_seeds.map((seed) => (
                    <V4Chip key={seed}>{seed}</V4Chip>
                  ))}
                </div>
              </label>
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm"
                disabled={busyId === "policy"}
                onClick={() => void savePolicy()}
              >
                Save policy
              </button>
            </V4Card>
          ) : null}
        </>
      )}
    </HivePageShell>
  );
}
