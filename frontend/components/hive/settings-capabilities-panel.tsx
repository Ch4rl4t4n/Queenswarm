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
    <article className="rounded-xl border border-(--qs-border) bg-black/25 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-sm font-semibold text-(--qs-text)">{cap.name}</h4>
            <V4Badge tone={STATUS_TONE[cap.status]}>{cap.status}</V4Badge>
            <InfoHint
              title={cap.name}
              description={cap.howItWorks}
              options={[cap.value, cap.competitiveEdge]}
            />
          </div>
          <p className="mt-2 text-xs leading-relaxed text-(--qs-text-3)">{cap.summary}</p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-1.5">
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
            disabled={busy !== null}
            onClick={() => void exportOne("txt")}
          >
            {busy === "txt" ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
            TXT
          </button>
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
            disabled={busy !== null}
            onClick={() => void exportOne("md")}
          >
            {busy === "md" ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
            MD
          </button>
        </div>
      </div>
      <dl className="mt-3 space-y-2 text-xs">
        <div>
          <dt className="font-medium text-(--qs-text-2)">Ako funguje</dt>
          <dd className="mt-0.5 text-(--qs-text-3)">{cap.howItWorks}</dd>
        </div>
        <div>
          <dt className="font-medium text-(--qs-text-2)">Prínos</dt>
          <dd className="mt-0.5 text-(--qs-text-3)">{cap.value}</dd>
        </div>
        <div>
          <dt className="font-medium text-pollen">Edge oproti konkurencii</dt>
          <dd className="mt-0.5 text-(--qs-text-3)">{cap.competitiveEdge}</dd>
        </div>
        {cap.routes?.length ? (
          <div>
            <dt className="font-medium text-(--qs-text-2)">Routes</dt>
            <dd className="mt-0.5 font-mono text-[11px] text-cyan">{cap.routes.join(" · ")}</dd>
          </div>
        ) : null}
      </dl>
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
    <article className="rounded-xl border border-(--qs-border) bg-black/20 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-sm font-semibold text-(--qs-text)">{item.name}</h4>
            <span
              className={cn(
                "rounded border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                PRIORITY_TONE[item.priority],
              )}
            >
              {item.priority}
            </span>
            <span className="text-[10px] text-(--qs-text-3)">{IMPACT_LABEL[item.impact]}</span>
            {item.week ? (
              <span className="text-[10px] text-cyan">Týždeň {item.week}</span>
            ) : null}
            {item.owner ? (
              <span className="text-[10px] uppercase text-(--qs-text-3)">{item.owner}</span>
            ) : null}
            {item.hints ? (
              <InfoHint title={item.name} description={item.hints} options={[item.rationale, item.competitiveEdge]} />
            ) : null}
          </div>
          <p className="mt-2 text-xs text-(--qs-text-3)">{item.summary}</p>
        </div>
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm shrink-0"
          disabled={busy}
          onClick={() => void exportPlanned()}
        >
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : "MD"}
        </button>
      </div>
      <p className="mt-3 text-xs text-(--qs-text-3)">
        <span className="font-medium text-(--qs-text-2)">Prečo: </span>
        {item.rationale}
      </p>
      <p className="mt-2 text-xs text-pollen/90">{item.competitiveEdge}</p>
      {item.auditGate ? (
        <p className="mt-2 font-mono text-[10px] text-cyan/80">Audit: {item.auditGate}</p>
      ) : null}
      {item.targetPhase ? (
        <p className="mt-2 text-[10px] uppercase tracking-wide text-(--qs-text-3)">Fáza: {item.targetPhase}</p>
      ) : null}
    </article>
  );
}

/** Settings — platform capabilities atlas with architecture map and exports. */
export function SettingsCapabilitiesPanel(): JSX.Element {
  const [exportBusy, setExportBusy] = useState<string | null>(null);
  const grouped = useMemo(() => groupCapabilitiesBySection(LIVE_PLATFORM_CAPABILITIES), []);
  const plannedPhases = useMemo(() => groupPlannedByRolloutPhase(PLANNED_PLATFORM_CAPABILITIES), []);

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
        <div className="space-y-6">
          {grouped.map(({ section, items }) => (
            <section key={section}>
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-pollen">
                {section}
                <span className="text-xs font-normal text-(--qs-text-3)">({items.length})</span>
              </h3>
              <div className="grid gap-3 lg:grid-cols-2">
                {items.map((cap) => (
                  <CapabilityCard key={cap.id} cap={cap} />
                ))}
              </div>
            </section>
          ))}
        </div>
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
        <p className="mb-4 flex items-start gap-2 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-xs text-(--qs-text-3)">
          <HelpCircle className="mt-0.5 h-4 w-4 shrink-0 text-pollen" aria-hidden />
          Fáza 0 = revenue + Exec Assistant wizard. P0 = blocker (Stripe, tier gates). Synced with{" "}
          <code className="text-cyan">docs/MISSION_EXECUTION_BACKLOG.md</code>.
        </p>
        <div className="space-y-8">
          {plannedPhases.map(({ phase, label, items }) => (
            <section key={phase}>
              <h3 className="mb-3 text-sm font-semibold text-pollen">{label}</h3>
              <div className="grid gap-3 lg:grid-cols-2">
                {items.map((item) => (
                  <PlannedCard key={item.id} item={item} />
                ))}
              </div>
            </section>
          ))}
        </div>
      </V4Card>
    </div>
  );
}
