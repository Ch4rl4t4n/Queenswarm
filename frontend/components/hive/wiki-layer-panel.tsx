"use client";

import { BookMarked, Download, Flower2, Loader2Icon, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { KnowledgeElicitationPanel } from "@/components/hive/knowledge-elicitation-panel";
import { SecondBrainCaptureApprovePanel } from "@/components/hive/second-brain-capture-approve-panel";
import { SecondBrainCapturePanel } from "@/components/hive/second-brain-capture-panel";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, V4Card, V4CardHeader, V4FormField, V4FormStack } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson, hivePutJson } from "@/lib/api";

interface WikiZoneOverview {
  count: number;
  char_count?: number;
  description: string;
  items?: Array<{
    layer: string;
    source_type: string;
    id: string;
    label: string;
    preview: string;
    verified?: boolean;
  }>;
  pages?: Array<{
    slug: string;
    title: string;
    char_count: number;
    version: number;
  }>;
  preview?: string;
}

interface WikiOverview {
  zones: {
    raw: WikiZoneOverview;
    wiki: WikiZoneOverview;
    instructions: WikiZoneOverview;
  };
  curated_prefix_chars: number;
  wiki_chars: number;
  settings?: {
    retrieval_tier: string;
    telemetry?: Record<string, number | string>;
  };
}

interface WikiSettings {
  retrieval_tier: "wiki_only" | "deep_raw";
  feature_enabled: boolean;
  telemetry: Record<string, number | string>;
}

interface GardenerRun {
  id: string;
  status: string;
  summary_md: string;
  pages_updated: number;
  raw_scanned: number;
  pollen_awarded: number;
  completed_at?: string | null;
}

const TIER_OPTIONS = [
  { value: "wiki_only", label: "Wiki only — hot tier (curated + compiled wiki)" },
  { value: "deep_raw", label: "Deep raw — include forager scrape + vectors" },
] as const;

/** Knowledge hub — Karpathy-style Wiki Layer (raw / wiki / instructions). */
export function WikiLayerPanel(): JSX.Element {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [overview, setOverview] = useState<WikiOverview | null>(null);
  const [settings, setSettings] = useState<WikiSettings | null>(null);
  const [lastRun, setLastRun] = useState<GardenerRun | null>(null);
  const [activePage, setActivePage] = useState<string | null>(null);
  const [pageContent, setPageContent] = useState<string>("");

  const reload = useCallback(async () => {
    try {
      const [ov, cfg, run] = await Promise.all([
        hiveGet<WikiOverview>("memory/wiki-layer/overview"),
        hiveGet<WikiSettings>("memory/wiki-layer/settings"),
        hiveGet<GardenerRun | null>("memory/wiki-layer/gardener/latest"),
      ]);
      setOverview(ov);
      setSettings(cfg);
      setLastRun(run);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Wiki Layer unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const loadPage = useCallback(async (slug: string) => {
    setActivePage(slug);
    try {
      const body = await hiveGet<{ content_md: string }>(`memory/wiki-layer/pages/${encodeURIComponent(slug)}`);
      setPageContent(body.content_md);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Page load failed.");
      setPageContent("");
    }
  }, []);

  async function saveTier(tier: "wiki_only" | "deep_raw") {
    setBusy(true);
    try {
      const body = await hivePutJson<WikiSettings>("memory/wiki-layer/settings", { retrieval_tier: tier });
      setSettings(body);
      toast.success("Retrieval tier saved.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Save failed.");
    } finally {
      setBusy(false);
    }
  }

  async function runGardener() {
    setBusy(true);
    try {
      const run = await hivePostJson<GardenerRun>("memory/wiki-layer/gardener/run", {});
      setLastRun(run);
      toast.success(`Wiki Gardener updated ${run.pages_updated} page(s).`);
      await reload();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Gardener run failed.");
    } finally {
      setBusy(false);
    }
  }

  async function exportVault() {
    setBusy(true);
    try {
      const res = await fetch("/api/v1/memory/wiki-layer/export/obsidian", { credentials: "include" });
      if (!res.ok) throw new Error("Export failed.");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "queenswarm-wiki-vault.zip";
      anchor.click();
      URL.revokeObjectURL(url);
      toast.success("Obsidian vault downloaded.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Export failed.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <V4Card>
        <div className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2Icon className="size-4 animate-spin" aria-hidden />
          Loading Wiki Layer…
        </div>
      </V4Card>
    );
  }

  const telemetry = settings?.telemetry ?? overview?.settings?.telemetry ?? {};

  return (
    <div className="space-y-4">
      <KnowledgeElicitationPanel />
      <SecondBrainCapturePanel onCaptured={() => void reload()} />
      <div id="second-brain-capture-approve" className="scroll-mt-28">
        <SecondBrainCaptureApprovePanel onApproved={() => void reload()} />
      </div>
      <V4Card>
        <V4CardHeader
          title="Wiki Layer"
          description="Karpathy-style hot/cold tier — compiled wiki every prompt; raw sources for deep research only."
          hint={sectionHintNode("knowledgeWikiLayer")}
          actions={
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1"
                disabled={busy}
                onClick={() => void exportVault()}
              >
                <Download className="size-3.5" aria-hidden />
                Obsidian export
                {sectionHintNode("knowledgeWikiObsidian")}
              </button>
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm inline-flex items-center gap-1"
                disabled={busy}
                onClick={() => void runGardener()}
              >
                {busy ? <Loader2Icon className="size-3.5 animate-spin" aria-hidden /> : <RefreshCw className="size-3.5" aria-hidden />}
                Run Wiki Gardener
                {sectionHintNode("knowledgeWikiGardener")}
              </button>
            </div>
          }
        />

        <V4FormStack>
          <V4FormField
            label="Retrieval tier"
            footer={sectionHintNode("knowledgeWikiRetrievalTier")}
          >
            <QsSelect
              value={settings?.retrieval_tier ?? "wiki_only"}
              options={TIER_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
              onValueChange={(v) => void saveTier(v as "wiki_only" | "deep_raw")}
              disabled={busy}
            />
          </V4FormField>
        </V4FormStack>

        {lastRun ? (
          <p className="mt-3 text-xs text-muted-foreground">
            Last gardener: {lastRun.summary_md}
            {lastRun.pollen_awarded > 0 ? (
              <span className="ml-2 inline-flex items-center gap-1 text-(--qs-pollen)">
                <Flower2 className="size-3" aria-hidden />+{lastRun.pollen_awarded} pollen
              </span>
            ) : null}
          </p>
        ) : null}
      </V4Card>

      <V4Card className="border-none bg-transparent shadow-none">
        <V4CardHeader
          title="Memory zones"
          description="What the Queen sees (hot) vs cold storage — char counts refresh after each Gardener run."
          hint={sectionHintNode("knowledgeWikiZones")}
        />
      </V4Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <ZoneCard
          title="Raw"
          badge={`${overview?.zones.raw.count ?? 0} sources`}
          description={overview?.zones.raw.description ?? ""}
          tone="magenta"
        >
          <ul className="space-y-2 text-xs">
            {(overview?.zones.raw.items ?? []).slice(0, 6).map((item) => (
              <li key={item.id} className="rounded border border-white/5 bg-white/[0.02] p-2">
                <span className="font-mono text-(--qs-cyan)">{item.label}</span>
                <p className="mt-1 text-muted-foreground">{item.preview}</p>
              </li>
            ))}
          </ul>
        </ZoneCard>

        <ZoneCard
          title="Wiki"
          badge={`${overview?.wiki_chars ?? 0} chars`}
          description={overview?.zones.wiki.description ?? ""}
          tone="amber"
        >
          <ul className="space-y-1 text-sm">
            {(overview?.zones.wiki.pages ?? []).map((page) => (
              <li key={page.slug}>
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--sm w-full justify-start"
                  onClick={() => void loadPage(page.slug)}
                >
                  <BookMarked className="size-3.5 shrink-0" aria-hidden />
                  {page.title}
                  <V4Badge tone="gold" className="ml-auto">
                    v{page.version}
                  </V4Badge>
                </button>
              </li>
            ))}
          </ul>
          {activePage && pageContent ? (
            <pre className="mt-3 max-h-48 overflow-auto rounded bg-black/30 p-2 text-xs whitespace-pre-wrap">
              {pageContent}
            </pre>
          ) : null}
        </ZoneCard>

        <ZoneCard
          title="Instructions"
          badge={`${overview?.zones.instructions.char_count ?? 0} chars`}
          description={overview?.zones.instructions.description ?? ""}
          tone="green"
        >
          <p className="text-xs text-muted-foreground">{overview?.zones.instructions.preview ?? "—"}</p>
          <p className="mt-2 text-xs">
            Curated prefix: <span className="font-mono text-(--qs-cyan)">{overview?.curated_prefix_chars ?? 0}</span> chars
          </p>
        </ZoneCard>
      </div>

      <V4Card>
        <V4CardHeader title="Token telemetry" description="Verify wiki layer saves tokens vs raw RAG fallback." hint={sectionHintNode("knowledgeWikiTelemetry")} />
        <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
          <TelemetryStat label="Curated prefix" value={telemetry.curated_prefix_chars} />
          <TelemetryStat label="Wiki block" value={telemetry.wiki_chars ?? overview?.wiki_chars} />
          <TelemetryStat label="RAG chunks" value={telemetry.rag_chunks} />
          <TelemetryStat label="Raw fallback hits" value={telemetry.raw_fallback_hits} />
        </dl>
      </V4Card>
    </div>
  );
}

function ZoneCard({
  title,
  badge,
  description,
  tone,
  children,
}: {
  title: string;
  badge: string;
  description: string;
  tone: "amber" | "cyan" | "green" | "magenta";
  children: React.ReactNode;
}): JSX.Element {
  const glow =
    tone === "amber"
      ? "border-(--qs-pollen)/30"
      : tone === "green"
        ? "border-(--qs-green)/30"
        : tone === "magenta"
          ? "border-(--qs-magenta)/30"
          : "border-(--qs-cyan)/30";

  return (
    <V4Card className={glow}>
      <V4CardHeader title={title} description={description} actions={<V4Badge tone="info">{badge}</V4Badge>} />
      {children}
    </V4Card>
  );
}

function TelemetryStat({ label, value }: { label: string; value: unknown }): JSX.Element {
  const display = value === undefined || value === null || value === "" ? "—" : String(value);
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="font-mono text-base text-(--qs-cyan)">{display}</dd>
    </div>
  );
}
