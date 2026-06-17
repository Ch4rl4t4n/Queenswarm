"use client";

import {
  Download,
  FileText,
  HelpCircle,
  Layers,
  Loader2,
  Printer,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { CollapsibleLazyPanel } from "@/components/hive/collapsible-lazy-panel";
import { InfoHint } from "@/components/hive/info-hint";
import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { hiveGet, hivePostJson } from "@/lib/api";
import {
  LIVE_PLATFORM_CAPABILITIES,
  PLANNED_PLATFORM_CAPABILITIES,
  PLATFORM_ARCHITECTURE_LAYERS,
  MISSION_NORTH_STAR,
  groupCapabilitiesBySection,
  groupPlannedByRolloutPhase,
  type ArchitectureLayer,
  type PlatformCapability,
  type PlannedCapability,
} from "@/lib/platform-capabilities-catalog";
import {
  buildCapabilitiesMarkdown,
  buildCapabilitiesPlainText,
  buildSingleCapabilityMarkdown,
  buildSingleCapabilityPlainText,
  buildSinglePlannedMarkdown,
  downloadTextFile,
  printCapabilitiesPdf,
} from "@/lib/platform-capabilities-export";
import { CAPABILITIES_DENSITY_SECTIONS } from "@/lib/settings-panel-density";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";
import { cn } from "@/lib/utils";

const LAYER_TONE: Record<ArchitectureLayer["tone"], string> = {
  cyan: "border-cyan/35 bg-cyan/[0.06]",
  pollen: "border-pollen/35 bg-pollen/[0.06]",
  purple: "border-purple-400/35 bg-purple-400/[0.06]",
  green: "border-[#00FF88]/35 bg-[#00FF88]/[0.06]",
  magenta: "border-[#FF00AA]/35 bg-[#FF00AA]/[0.06]",
  zinc: "border-(--qs-border) bg-white/[0.03]",
};

const STATUS_TONE: Record<PlatformCapability["status"], "ok" | "info" | "warn"> = {
  live: "ok",
  beta: "info",
  flagged: "warn",
};

const PRIORITY_TONE: Record<PlannedCapability["priority"], string> = {
  P0: "text-[#FF3366] border-[#FF3366]/45",
  P1: "text-pollen border-pollen/45",
  P2: "text-cyan border-cyan/45",
  P3: "text-zinc-300 border-(--qs-border)",
  P4: "text-purple-300 border-purple-400/45",
};

const IMPACT_LABEL: Record<PlannedCapability["impact"], string> = {
  high: "High impact",
  medium: "Medium impact",
  low: "Low impact",
};

interface AtlasHighlightRow {
  capability_id: string;
  kind: "live" | "planned";
  reason: string;
  signal_title: string;
}

interface AtlasHighlightsSnapshot {
  enabled: boolean;
  unseen_count: number;
  highlight_count: number;
  signal_count: number;
  operator_hint: string;
  highlights: AtlasHighlightRow[];
}

function capabilityHighlightKey(kind: "live" | "planned", capabilityId: string): string {
  return `${kind}:${capabilityId}`;
}

function CapabilityCard({
  cap,
  highlight,
}: {
  cap: PlatformCapability;
  highlight?: AtlasHighlightRow;
}): JSX.Element {
  const [busy, setBusy] = useState<"md" | "txt" | null>(null);

  async function exportOne(format: "md" | "txt"): Promise<void> {
    setBusy(format);
    try {
      const stamp = new Date().toISOString().slice(0, 10);
      if (format === "md") {
        await downloadTextFile(
          buildSingleCapabilityMarkdown(cap),
          `queenswarm-${cap.id}-${stamp}.md`,
          "text/markdown;charset=utf-8",
        );
      } else {
        await downloadTextFile(
          buildSingleCapabilityPlainText(cap),
          `queenswarm-${cap.id}-${stamp}.txt`,
          "text/plain;charset=utf-8",
        );
      }
      toast.success(`Export ${cap.name} (${format.toUpperCase()})`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <article
      className={cn(
        "v4-dream-cycle-card flex h-full flex-col gap-3",
        highlight ? "ring-1 ring-pollen/50 shadow-[0_0_12px_rgba(255,184,0,0.15)]" : undefined,
      )}
      data-testid={highlight ? `capability-highlight-${cap.id}` : undefined}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-semibold text-(--qs-text)">{cap.name}</p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">{cap.section}</p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
          {highlight ? <V4Badge tone="gold">🟡 synthesis</V4Badge> : null}
          <V4Badge tone={STATUS_TONE[cap.status]}>{cap.status}</V4Badge>
          <InfoHint
            title={cap.name}
            description={cap.howItWorks}
            options={[cap.value, cap.competitiveEdge]}
          />
        </div>
      </div>

      <p className="text-xs leading-relaxed text-(--qs-text-3)">{cap.summary}</p>

      {highlight ? (
        <p className="rounded-xl border border-pollen/25 bg-pollen/[0.06] px-3 py-2 text-[11px] text-(--qs-text-2)">
          {highlight.reason} — <span className="text-(--qs-text-3)">{highlight.signal_title}</span>
        </p>
      ) : null}

      <div className="rounded-xl bg-cyan-500/5 px-3 py-2">
        <p className="v4-field-label text-[10px] text-cyan-300/90">How it works</p>
        <p className="mt-1 text-xs leading-relaxed text-(--qs-text-2)">{cap.howItWorks}</p>
      </div>

      <p className="font-mono text-[11px] text-(--qs-text-3)">
        {cap.routes?.length ? cap.routes.join(" · ") : cap.id}
      </p>

      <div className="flex flex-wrap gap-2">
        {cap.stack?.backend?.length ? <V4Badge tone="info">backend</V4Badge> : null}
        {cap.stack?.frontend?.length ? <V4Badge tone="purple">frontend</V4Badge> : null}
        {cap.status === "beta" ? <V4Badge tone="warn">beta</V4Badge> : null}
      </div>

      <div className="v4-dream-cycle-card-actions">
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
          disabled={busy !== null}
          onClick={() => void exportOne("txt")}
        >
          {busy === "txt" ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
          Export TXT
        </button>
        <button
          type="button"
          className="qs-btn qs-btn--primary qs-btn--sm gap-1"
          disabled={busy !== null}
          onClick={() => void exportOne("md")}
        >
          {busy === "md" ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
          Export MD
        </button>
      </div>
    </article>
  );
}

function PlannedCard({
  item,
  highlight,
}: {
  item: PlannedCapability;
  highlight?: AtlasHighlightRow;
}): JSX.Element {
  const [busy, setBusy] = useState(false);

  async function exportPlanned(): Promise<void> {
    setBusy(true);
    try {
      const stamp = new Date().toISOString().slice(0, 10);
      await downloadTextFile(
        buildSinglePlannedMarkdown(item),
        `queenswarm-planned-${item.id}-${stamp}.md`,
        "text/markdown;charset=utf-8",
      );
      toast.success(`Export ${item.name}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <article
      className={cn(
        "v4-dream-cycle-card flex h-full flex-col gap-3",
        highlight ? "ring-1 ring-pollen/50 shadow-[0_0_12px_rgba(255,184,0,0.15)]" : undefined,
      )}
      data-testid={highlight ? `planned-highlight-${item.id}` : undefined}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-semibold text-(--qs-text)">{item.name}</p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">
            {item.targetPhase ?? "roadmap"}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
          {highlight ? <V4Badge tone="gold">🟡 synthesis</V4Badge> : null}
          <span
            className={cn(
              "rounded border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
              PRIORITY_TONE[item.priority],
            )}
          >
            {item.priority}
          </span>
          {item.hints ? (
            <InfoHint title={item.name} description={item.hints} options={[item.rationale, item.competitiveEdge]} />
          ) : null}
        </div>
      </div>

      <p className="text-xs leading-relaxed text-(--qs-text-3)">{item.summary}</p>

      {highlight ? (
        <p className="rounded-xl border border-pollen/25 bg-pollen/[0.06] px-3 py-2 text-[11px] text-(--qs-text-2)">
          {highlight.reason} — <span className="text-(--qs-text-3)">{highlight.signal_title}</span>
        </p>
      ) : null}

      <div className="rounded-xl bg-pollen-500/5 px-3 py-2">
        <p className="v4-field-label text-[10px] text-pollen/90">Why</p>
        <p className="mt-1 text-xs leading-relaxed text-(--qs-text-2)">{item.rationale}</p>
      </div>

      <p className="text-xs text-pollen/90">{item.competitiveEdge}</p>

      <p className="font-mono text-[11px] text-(--qs-text-3)">
        {IMPACT_LABEL[item.impact]}
        {item.week ? ` · week ${item.week}` : ""}
        {item.owner ? ` · ${item.owner}` : ""}
      </p>

      <div className="flex flex-wrap gap-2">
        <V4Badge tone={item.impact === "high" ? "warn" : item.impact === "medium" ? "info" : "purple"}>
          {item.impact} impact
        </V4Badge>
        {item.auditGate ? <V4Badge tone="info">audit gate</V4Badge> : null}
      </div>

      {item.auditGate ? (
        <p className="font-mono text-[10px] text-cyan/80">Audit: {item.auditGate}</p>
      ) : null}

      <div className="v4-dream-cycle-card-actions">
        <button
          type="button"
          className="qs-btn qs-btn--primary qs-btn--sm gap-1"
          disabled={busy}
          onClick={() => void exportPlanned()}
        >
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
          Export MD
        </button>
      </div>
    </article>
  );
}

/** Settings — platform capabilities atlas with architecture map and exports. */
export function SettingsCapabilitiesPanel(): JSX.Element {
  const [exportBusy, setExportBusy] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<string>("all");
  const [activePhase, setActivePhase] = useState<string>("all");
  const [atlasHighlights, setAtlasHighlights] = useState<AtlasHighlightsSnapshot | null>(null);
  const [ackBusy, setAckBusy] = useState(false);
  const grouped = useMemo(() => groupCapabilitiesBySection(LIVE_PLATFORM_CAPABILITIES), []);
  const plannedPhases = useMemo(() => groupPlannedByRolloutPhase(PLANNED_PLATFORM_CAPABILITIES), []);
  const pageSize = useGridTwoRowPageSize({ columns: 2 });

  const highlightByKey = useMemo(() => {
    const map = new Map<string, AtlasHighlightRow>();
    for (const row of atlasHighlights?.highlights ?? []) {
      map.set(capabilityHighlightKey(row.kind, row.capability_id), row);
    }
    return map;
  }, [atlasHighlights]);

  const liveHighlightIds = useMemo(
    () =>
      new Set(
        (atlasHighlights?.highlights ?? [])
          .filter((row) => row.kind === "live")
          .map((row) => row.capability_id),
      ),
    [atlasHighlights],
  );

  const plannedHighlightIds = useMemo(
    () =>
      new Set(
        (atlasHighlights?.highlights ?? [])
          .filter((row) => row.kind === "planned")
          .map((row) => row.capability_id),
      ),
    [atlasHighlights],
  );

  useEffect(() => {
    let cancelled = false;
    void hiveGet<AtlasHighlightsSnapshot>("harness/capabilities-atlas/highlights")
      .then((payload) => {
        if (!cancelled) {
          setAtlasHighlights(payload);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAtlasHighlights(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const ackHighlights = useCallback(async () => {
    setAckBusy(true);
    try {
      await hivePostJson("harness/capabilities-atlas/highlights/ack", { ack_all: true });
      setAtlasHighlights((prev) => (prev ? { ...prev, unseen_count: 0 } : prev));
      toast.success("Synthesis highlights acknowledged");
    } catch {
      toast.error("Could not acknowledge highlights");
    } finally {
      setAckBusy(false);
    }
  }, []);

  const sectionTabs = useMemo(
    () => [
      { id: "all", label: "All", count: LIVE_PLATFORM_CAPABILITIES.length },
      ...(liveHighlightIds.size > 0
        ? [{ id: "highlighted", label: "🟡 Highlighted", count: liveHighlightIds.size }]
        : []),
      ...grouped.map(({ section, items }) => ({ id: section, label: section, count: items.length })),
    ],
    [grouped, liveHighlightIds.size],
  );

  const filteredCapabilities = useMemo(() => {
    if (activeSection === "highlighted") {
      return LIVE_PLATFORM_CAPABILITIES.filter((cap) => liveHighlightIds.has(cap.id));
    }
    if (activeSection === "all") {
      return LIVE_PLATFORM_CAPABILITIES;
    }
    return grouped.find(({ section }) => section === activeSection)?.items ?? [];
  }, [activeSection, grouped, liveHighlightIds]);

  const capabilitiesPagination = usePaginatedSlice(
    filteredCapabilities,
    pageSize,
    `${activeSection}|${pageSize}`,
  );

  const phaseTabs = useMemo(
    () => [
      { id: "all", label: "All", count: PLANNED_PLATFORM_CAPABILITIES.length },
      ...(plannedHighlightIds.size > 0
        ? [{ id: "highlighted", label: "🟡 Highlighted", count: plannedHighlightIds.size }]
        : []),
      ...plannedPhases.map(({ phase, label, items }) => ({ id: phase, label, count: items.length })),
    ],
    [plannedPhases, plannedHighlightIds.size],
  );

  const filteredPlanned = useMemo(() => {
    if (activePhase === "highlighted") {
      return PLANNED_PLATFORM_CAPABILITIES.filter((item) => plannedHighlightIds.has(item.id));
    }
    if (activePhase === "all") {
      return PLANNED_PLATFORM_CAPABILITIES;
    }
    return plannedPhases.find(({ phase }) => phase === activePhase)?.items ?? [];
  }, [activePhase, plannedPhases, plannedHighlightIds]);

  const plannedPagination = usePaginatedSlice(filteredPlanned, pageSize, `${activePhase}|${pageSize}`);

  const exportAll = useCallback(async (kind: "md" | "txt" | "pdf") => {
    setExportBusy(kind);
    try {
      const stamp = new Date().toISOString().slice(0, 10);
      if (kind === "pdf") {
        const ok = printCapabilitiesPdf();
        if (!ok) {
          toast.error("Allow pop-ups to export PDF.");
          return;
        }
        toast.success("Print dialog opened — save as PDF");
        return;
      }
      if (kind === "md") {
        await downloadTextFile(
          buildCapabilitiesMarkdown(),
          `queenswarm-capabilities-atlas-${stamp}.md`,
          "text/markdown;charset=utf-8",
        );
      } else {
        await downloadTextFile(
          buildCapabilitiesPlainText(),
          `queenswarm-capabilities-atlas-${stamp}.txt`,
          "text/plain;charset=utf-8",
        );
      }
      toast.success(`Atlas exported (${kind.toUpperCase()})`);
    } finally {
      setExportBusy(null);
    }
  }, []);

  return (
    <div className="settings-panel-density space-y-4" data-testid="settings-capabilities-panel">
      <V4Card className="overflow-hidden p-0" id={CAPABILITIES_DENSITY_SECTIONS[0]?.id}>
        <div className="border-b border-(--qs-border) px-4 py-4 md:px-6">
          <V4CardHeader
            as="h2"
            kicker="Settings · Atlas"
            title="Platform capabilities"
            description="Full overview of live features, BE/FE architecture, and roadmap with PDF and text export."
          />
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm gap-2"
              disabled={exportBusy !== null}
              onClick={() => void exportAll("pdf")}
            >
              {exportBusy === "pdf" ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Printer className="h-4 w-4" aria-hidden />
              )}
              Export PDF
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm gap-2"
              disabled={exportBusy !== null}
              onClick={() => void exportAll("md")}
            >
              {exportBusy === "md" ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <FileText className="h-4 w-4" aria-hidden />
              )}
              Markdown
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm gap-2"
              disabled={exportBusy !== null}
              onClick={() => void exportAll("txt")}
            >
              {exportBusy === "txt" ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Download className="h-4 w-4" aria-hidden />
              )}
              Text
            </button>
          </div>
        </div>
      </V4Card>

      {atlasHighlights?.enabled && atlasHighlights.unseen_count > 0 ? (
        <V4Card data-testid="capabilities-atlas-synthesis-banner" className="border-pollen/30">
          <V4CardHeader
            kicker="SIG3"
            title="External synthesis diff"
            description={atlasHighlights.operator_hint}
            actions={<V4Badge tone="gold">{atlasHighlights.unseen_count} new</V4Badge>}
          />
          <div className="flex flex-wrap gap-2 px-4 pb-4">
            <V4Badge tone="info">{atlasHighlights.signal_count} signals</V4Badge>
            <V4Badge tone="warn">{atlasHighlights.highlight_count} atlas rows</V4Badge>
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              disabled={ackBusy}
              onClick={() => void ackHighlights()}
            >
              {ackBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
              Acknowledge
            </button>
          </div>
        </V4Card>
      ) : null}

      <V4Card id={CAPABILITIES_DENSITY_SECTIONS[1]?.id}>
        <V4CardHeader
          as="h2"
          kicker={`${LIVE_PLATFORM_CAPABILITIES.length} live`}
          title="Live features"
          description="Each item has a hint, value summary, and TXT/MD export."
          actions={
            <span className="flex items-center gap-1.5 text-xs text-(--qs-text-3)">
              <Layers className="h-3.5 w-3.5" aria-hidden />
              {grouped.length} sections
            </span>
          }
        />
        <div className="v4-subtab-row w-full max-w-full">
          {sectionTabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={cn("v4-subtab shrink-0 gap-2", activeSection === tab.id && "v4-subtab--active")}
              onClick={() => setActiveSection(tab.id)}
            >
              {tab.label}
              <span className="rounded-full bg-white/10 px-1.5 py-0.5 font-mono text-[10px] text-(--qs-text-3)">
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        <div className="mt-4 flex shrink-0 items-center justify-between gap-2">
          <p className="v4-field-label">
            {activeSection === "all" ? "All capabilities" : activeSection} ({filteredCapabilities.length})
          </p>
        </div>

        <ViewportBoundedPanel
          className="v4-recipe-catalog-panel mt-3"
          footer={
            <ListPaginator
              page={capabilitiesPagination.page}
              totalPages={capabilitiesPagination.totalPages}
              totalItems={capabilitiesPagination.totalItems}
              pageSize={pageSize}
              onPageChange={capabilitiesPagination.setPage}
            />
          }
        >
          <div className="grid gap-3 md:grid-cols-2">
            {capabilitiesPagination.slice.map((cap) => (
              <CapabilityCard
                key={cap.id}
                cap={cap}
                highlight={highlightByKey.get(capabilityHighlightKey("live", cap.id))}
              />
            ))}
          </div>
        </ViewportBoundedPanel>
      </V4Card>

      <CollapsibleLazyPanel
        id="capabilities-mission"
        hashKey="capabilities-mission"
        title="North Star & rollout"
        hint="Mission metric · Phase 0 timeline"
        meta="Advanced"
        lazyContent={() => (
          <V4Card className="border-pollen/25 border-0 bg-transparent p-0 shadow-none">
            <V4CardHeader
              as="h2"
              kicker="Mission · May 2026"
              title="North Star & rollout"
              description={MISSION_NORTH_STAR.tagline}
            />
            <dl className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2.5">
                <dt className="text-[10px] font-semibold uppercase tracking-wide text-pollen">Metric</dt>
                <dd className="mt-1 text-sm text-(--qs-text)">{MISSION_NORTH_STAR.metric}</dd>
              </div>
              <div className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2.5">
                <dt className="text-[10px] font-semibold uppercase tracking-wide text-pollen">Phase 0</dt>
                <dd className="mt-1 text-sm text-(--qs-text)">
                  {MISSION_NORTH_STAR.phase0Weeks} weeks · ~{MISSION_NORTH_STAR.phase0Hours} h
                </dd>
              </div>
            </dl>
            <p className="mt-3 text-xs text-(--qs-text-3)">
              Full backlog: <code className="text-cyan">docs/MISSION_EXECUTION_BACKLOG.md</code> · runbook:{" "}
              <code className="text-cyan">docs/TOMORROW_OPERATOR_RUNBOOK.md</code>
            </p>
          </V4Card>
        )}
      />

      <CollapsibleLazyPanel
        id="capabilities-architecture"
        hashKey="capabilities-architecture"
        title="Backend + Frontend stack"
        hint="Architecture map · data layers"
        meta={`${PLATFORM_ARCHITECTURE_LAYERS.length} layers`}
        lazyContent={() => (
          <div className="capabilities-arch-flow space-y-3">
            {PLATFORM_ARCHITECTURE_LAYERS.map((layer, index) => (
              <div key={layer.id} className="capabilities-arch-layer">
                {index > 0 ? (
                  <div className="flex justify-center py-1" aria-hidden>
                    <span className="text-lg text-pollen/70">↓</span>
                  </div>
                ) : null}
                <div className={cn("rounded-xl border p-4", LAYER_TONE[layer.tone])}>
                  <p className="text-[11px] font-semibold uppercase tracking-widest text-(--qs-text-2)">
                    {layer.label}
                  </p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {layer.nodes.map((node) => (
                      <div
                        key={node.id}
                        className="rounded-lg border border-(--qs-border)/80 bg-black/30 px-3 py-2.5"
                      >
                        <p className="text-sm font-medium text-(--qs-text)">{node.label}</p>
                        <p className="mt-1 text-[11px] leading-relaxed text-(--qs-text-3)">{node.detail}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      />

      <CollapsibleLazyPanel
        id="capabilities-roadmap"
        hashKey="capabilities-roadmap"
        title="Planned features"
        hint="Roadmap · P0 blockers · rollout phases"
        meta={`${PLANNED_PLATFORM_CAPABILITIES.length} items`}
        lazyContent={() => (
          <>
            <p className="mb-4 flex items-start gap-2 rounded-lg border border-pollen/20 bg-pollen/[0.04] px-3 py-2 text-xs text-(--qs-text-3)">
              <HelpCircle className="mt-0.5 h-4 w-4 shrink-0 text-pollen" aria-hidden />
              Phase 0 = revenue + Exec Assistant wizard. P0 = operator blockers + tier gates. Synced with{" "}
              <code className="text-cyan">docs/MISSION_EXECUTION_BACKLOG.md</code>.
            </p>

            <div className="v4-subtab-row w-full max-w-full">
              {phaseTabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  className={cn("v4-subtab shrink-0 gap-2", activePhase === tab.id && "v4-subtab--active")}
                  onClick={() => setActivePhase(tab.id)}
                >
                  {tab.label}
                  <span className="rounded-full bg-white/10 px-1.5 py-0.5 font-mono text-[10px] text-(--qs-text-3)">
                    {tab.count}
                  </span>
                </button>
              ))}
            </div>

            <div className="mt-4 flex shrink-0 items-center justify-between gap-2">
              <p className="v4-field-label">
                {activePhase === "all" ? "All planned" : phaseTabs.find((t) => t.id === activePhase)?.label} (
                {filteredPlanned.length})
              </p>
            </div>

            <ViewportBoundedPanel
              className="v4-recipe-catalog-panel mt-3"
              footer={
                <ListPaginator
                  page={plannedPagination.page}
                  totalPages={plannedPagination.totalPages}
                  totalItems={plannedPagination.totalItems}
                  pageSize={pageSize}
                  onPageChange={plannedPagination.setPage}
                />
              }
            >
              <div className="grid gap-3 md:grid-cols-2">
                {plannedPagination.slice.map((item) => (
                  <PlannedCard
                    key={item.id}
                    item={item}
                    highlight={highlightByKey.get(capabilityHighlightKey("planned", item.id))}
                  />
                ))}
              </div>
            </ViewportBoundedPanel>
          </>
        )}
      />
    </div>
  );
}
