"use client";

import {
  Download,
  FileText,
  HelpCircle,
  Layers,
  Loader2,
  Map,
  Printer,
  Rocket,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

import { InfoHint } from "@/components/hive/info-hint";
import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
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
  high: "Vysoký dopad",
  medium: "Stredný dopad",
  low: "Nízky dopad",
};

function CapabilityCard({ cap }: { cap: PlatformCapability }): JSX.Element {
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
    <article className="v4-dream-cycle-card flex h-full flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-semibold text-(--qs-text)">{cap.name}</p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">{cap.section}</p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
          <V4Badge tone={STATUS_TONE[cap.status]}>{cap.status}</V4Badge>
          <InfoHint
            title={cap.name}
            description={cap.howItWorks}
            options={[cap.value, cap.competitiveEdge]}
          />
        </div>
      </div>

      <p className="text-xs leading-relaxed text-(--qs-text-3)">{cap.summary}</p>

      <div className="rounded-xl bg-cyan-500/5 px-3 py-2">
        <p className="v4-field-label text-[10px] text-cyan-300/90">Ako funguje</p>
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

      <div className="mt-auto flex flex-wrap gap-1.5">
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
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
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

function PlannedCard({ item }: { item: PlannedCapability }): JSX.Element {
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
    <article className="v4-dream-cycle-card flex h-full flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-semibold text-(--qs-text)">{item.name}</p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">
            {item.targetPhase ?? "roadmap"}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
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

      <div className="rounded-xl bg-pollen-500/5 px-3 py-2">
        <p className="v4-field-label text-[10px] text-pollen/90">Prečo</p>
        <p className="mt-1 text-xs leading-relaxed text-(--qs-text-2)">{item.rationale}</p>
      </div>

      <p className="text-xs text-pollen/90">{item.competitiveEdge}</p>

      <p className="font-mono text-[11px] text-(--qs-text-3)">
        {IMPACT_LABEL[item.impact]}
        {item.week ? ` · týždeň ${item.week}` : ""}
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

      <div className="mt-auto flex flex-wrap gap-1.5">
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
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
  const grouped = useMemo(() => groupCapabilitiesBySection(LIVE_PLATFORM_CAPABILITIES), []);
  const plannedPhases = useMemo(() => groupPlannedByRolloutPhase(PLANNED_PLATFORM_CAPABILITIES), []);
  const pageSize = useGridTwoRowPageSize({ columns: 2 });

  const sectionTabs = useMemo(
    () => [
      { id: "all", label: "All", count: LIVE_PLATFORM_CAPABILITIES.length },
      ...grouped.map(({ section, items }) => ({ id: section, label: section, count: items.length })),
    ],
    [grouped],
  );

  const filteredCapabilities = useMemo(() => {
    if (activeSection === "all") {
      return LIVE_PLATFORM_CAPABILITIES;
    }
    return grouped.find(({ section }) => section === activeSection)?.items ?? [];
  }, [activeSection, grouped]);

  const capabilitiesPagination = usePaginatedSlice(
    filteredCapabilities,
    pageSize,
    `${activeSection}|${pageSize}`,
  );

  const phaseTabs = useMemo(
    () => [
      { id: "all", label: "All", count: PLANNED_PLATFORM_CAPABILITIES.length },
      ...plannedPhases.map(({ phase, label, items }) => ({ id: phase, label, count: items.length })),
    ],
    [plannedPhases],
  );

  const filteredPlanned = useMemo(() => {
    if (activePhase === "all") {
      return PLANNED_PLATFORM_CAPABILITIES;
    }
    return plannedPhases.find(({ phase }) => phase === activePhase)?.items ?? [];
  }, [activePhase, plannedPhases]);

  const plannedPagination = usePaginatedSlice(filteredPlanned, pageSize, `${activePhase}|${pageSize}`);

  const exportAll = useCallback(async (kind: "md" | "txt" | "pdf") => {
    setExportBusy(kind);
    try {
      const stamp = new Date().toISOString().slice(0, 10);
      if (kind === "pdf") {
        const ok = printCapabilitiesPdf();
        if (!ok) {
          toast.error("Povoľ popup okno pre export PDF.");
          return;
        }
        toast.success("Otvorený tlačový dialóg — ulož ako PDF");
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
      toast.success(`Atlas exportovaný (${kind.toUpperCase()})`);
    } finally {
      setExportBusy(null);
    }
  }, []);

  return (
    <div className="space-y-6">
      <V4Card className="overflow-hidden p-0">
        <div className="border-b border-(--qs-border) px-4 py-4 md:px-6">
          <V4CardHeader
            as="h2"
            kicker="Settings · Atlas"
            title="Platform capabilities"
            description="Kompletný prehľad live featur, architektúry BE/FE a roadmapu s exportom do PDF a textu."
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

      <V4Card className="border-pollen/25">
        <V4CardHeader
          as="h2"
          kicker="Mission · máj 2026"
          title="North Star & rollout"
          description={MISSION_NORTH_STAR.tagline}
        />
        <dl className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2.5">
            <dt className="text-[10px] font-semibold uppercase tracking-wide text-pollen">Metrika</dt>
            <dd className="mt-1 text-sm text-(--qs-text)">{MISSION_NORTH_STAR.metric}</dd>
          </div>
          <div className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2.5">
            <dt className="text-[10px] font-semibold uppercase tracking-wide text-pollen">Fáza 0</dt>
            <dd className="mt-1 text-sm text-(--qs-text)">
              {MISSION_NORTH_STAR.phase0Weeks} týždne · ~{MISSION_NORTH_STAR.phase0Hours} h
            </dd>
          </div>
        </dl>
        <p className="mt-3 text-xs text-(--qs-text-3)">
          Detailný backlog: <code className="text-cyan">docs/MISSION_EXECUTION_BACKLOG.md</code> · zajtra:{" "}
          <code className="text-cyan">docs/TOMORROW_OPERATOR_RUNBOOK.md</code>
        </p>
      </V4Card>

      <V4Card id="capabilities-architecture" className="scroll-mt-28">
        <V4CardHeader
          as="h2"
          kicker="Architecture map"
          title="Backend + Frontend stack"
          description="Tok od Next.js cockpit cez FastAPI až po dátové vrstvy a LLM router."
          actions={
            <span className="flex items-center gap-1.5 text-xs text-(--qs-text-3)">
              <Map className="h-3.5 w-3.5" aria-hidden />
              {PLATFORM_ARCHITECTURE_LAYERS.length} vrstiev
            </span>
          }
        />
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
      </V4Card>

      <V4Card>
        <V4CardHeader
          as="h2"
          kicker={`${LIVE_PLATFORM_CAPABILITIES.length} live`}
          title="Funkčné features"
          description="Každá položka má hint, popis prínosu a export TXT/MD."
          actions={
            <span className="flex items-center gap-1.5 text-xs text-(--qs-text-3)">
              <Layers className="h-3.5 w-3.5" aria-hidden />
              {grouped.length} sekcií
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
              <CapabilityCard key={cap.id} cap={cap} />
            ))}
          </div>
        </ViewportBoundedPanel>
      </V4Card>

      <V4Card>
        <V4CardHeader
          as="h2"
          kicker="Roadmap"
          title="Plánované features"
          description="Priorita zapracovania (P0 = blocker) a očakávaný dopad na produkt."
          actions={
            <span className="flex items-center gap-1.5 text-xs text-(--qs-text-3)">
              <Rocket className="h-3.5 w-3.5" aria-hidden />
              {PLANNED_PLATFORM_CAPABILITIES.length} položiek
            </span>
          }
        />
        <p className="mb-4 flex items-start gap-2 rounded-lg border border-pollen/20 bg-pollen/[0.04] px-3 py-2 text-xs text-(--qs-text-3)">
          <HelpCircle className="mt-0.5 h-4 w-4 shrink-0 text-pollen" aria-hidden />
          Fáza 0 = revenue + Exec Assistant wizard. P0 = blocker (Stripe, tier gates). Synced with{" "}
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
              <PlannedCard key={item.id} item={item} />
            ))}
          </div>
        </ViewportBoundedPanel>
      </V4Card>
    </div>
  );
}
