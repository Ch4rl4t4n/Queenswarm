"use client";

import { Loader2, Pencil, Plus, Save, Trash2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePatchJson } from "@/lib/api";

type ChartType = "bar" | "line" | "kpi";

interface ChartBlock {
  id: string;
  chart_type: ChartType;
  title: string;
  labels: string[];
  values: number[];
  unit: string;
  source_citation: string;
}

interface ReportArtifact {
  deliverable_id: string;
  lineage_id: string;
  version: number;
  title: string;
  markdown_body: string;
  chart_blocks: ChartBlock[];
  task_id: string | null;
  task_href: string | null;
  session_id: string | null;
  session_href: string | null;
  session_status: string | null;
  editable: boolean;
}

interface ReportSnapshot {
  enabled: boolean;
  has_artifact: boolean;
  artifact: ReportArtifact | null;
  empty_hint: string;
}

function chartSeries(block: ChartBlock): Array<{ label: string; value: number }> {
  if (block.chart_type === "kpi") {
    return [{ label: block.title, value: block.values[0] ?? 0 }];
  }
  return block.labels.map((label, idx) => ({
    label,
    value: block.values[idx] ?? 0,
  }));
}

function ChartBlockPreview({ block }: { block: ChartBlock }): JSX.Element {
  const data = chartSeries(block);

  if (block.chart_type === "kpi") {
    const value = block.values[0] ?? 0;
    return (
      <div className="rounded-lg border border-white/10 bg-black/30 p-4">
        <p className="text-xs uppercase tracking-wide text-(--qs-text-3)">{block.title}</p>
        <p className="mt-1 font-mono text-2xl text-pollen">
          {value.toLocaleString()}
          {block.unit ? <span className="ml-1 text-sm text-(--qs-text-3)">{block.unit}</span> : null}
        </p>
        {block.source_citation ? (
          <p className="mt-2 text-xs text-cyan">{block.source_citation}</p>
        ) : null}
      </div>
    );
  }

  if (block.chart_type === "line") {
    return (
      <div className="h-48 rounded-lg border border-white/10 bg-black/30 p-3">
        <p className="mb-2 text-sm font-medium text-(--qs-text)">{block.title}</p>
        <ResponsiveContainer width="100%" height="85%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="label" tick={{ fill: "#9ca3af", fontSize: 10 }} />
            <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} />
            <Tooltip contentStyle={{ background: "#050510", border: "1px solid #00FFFF", borderRadius: 8 }} />
            <Line type="monotone" dataKey="value" stroke="#00FFFF" strokeWidth={2} dot={{ fill: "#00FFFF" }} />
          </LineChart>
        </ResponsiveContainer>
        {block.source_citation ? (
          <p className="mt-1 text-xs text-cyan">{block.source_citation}</p>
        ) : null}
      </div>
    );
  }

  return (
    <div className="h-48 rounded-lg border border-white/10 bg-black/30 p-3">
      <p className="mb-2 text-sm font-medium text-(--qs-text)">{block.title}</p>
      <ResponsiveContainer width="100%" height="85%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="label" tick={{ fill: "#9ca3af", fontSize: 10 }} />
          <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} />
          <Tooltip contentStyle={{ background: "#050510", border: "1px solid #00FFFF", borderRadius: 8 }} />
          <Bar dataKey="value" fill="#00FFFF" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      {block.source_citation ? (
        <p className="mt-1 text-xs text-cyan">{block.source_citation}</p>
      ) : null}
    </div>
  );
}

function MarkdownPreview({ content }: { content: string }): JSX.Element {
  const html = useMemo(() => {
    const escaped = content
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
    return escaped
      .replace(/^### (.+)$/gm, '<h3 class="text-pollen text-sm font-semibold mt-4 mb-1">$1</h3>')
      .replace(/^## (.+)$/gm, '<h2 class="text-pollen text-base font-bold mt-5 mb-1">$1</h2>')
      .replace(/^# (.+)$/gm, '<h2 class="text-pollen text-xl font-bold mt-6 mb-2">$1</h2>')
      .replace(/\*\*(.+?)\*\*/g, '<strong class="text-(--qs-text) font-semibold">$1</strong>')
      .replace(/`(.+?)`/g, '<code class="bg-black/40 text-cyan px-1 rounded text-[0.85em]">$1</code>')
      .replace(/^- (.+)$/gm, '<li class="my-1 text-(--qs-text-2)">$1</li>')
      .replaceAll(/\n\n/g, "<br><br>")
      .replaceAll(/\n/g, "<br>");
  }, [content]);

  return (
    <div
      className="hive-readable-prose max-h-[420px] overflow-auto rounded-lg border border-white/10 bg-black/25 p-4 text-sm leading-relaxed text-(--qs-text-2)"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

export function AnalyticsReportArtifactPanel(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<ReportSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<"preview" | "edit">("preview");
  const [markdown, setMarkdown] = useState("");
  const [blocks, setBlocks] = useState<ChartBlock[]>([]);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<ReportSnapshot>("analytics-workspace/report-artifact");
      setSnapshot(data);
      if (data.artifact) {
        setMarkdown(data.artifact.markdown_body);
        setBlocks(data.artifact.chart_blocks);
      }
    } catch {
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const save = useCallback(async () => {
    if (!snapshot?.artifact) return;
    setSaving(true);
    try {
      const updated = await hivePatchJson<ReportArtifact>(
        `analytics-workspace/report-artifact/${snapshot.artifact.deliverable_id}`,
        { markdown_body: markdown, chart_blocks: blocks },
      );
      toast.success(`Report saved · v${updated.version}`);
      setMode("preview");
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }, [blocks, load, markdown, snapshot?.artifact]);

  const addBlock = (): void => {
    setBlocks((prev) => [
      ...prev,
      {
        id: `chart-${prev.length + 1}`,
        chart_type: "kpi",
        title: "New metric",
        labels: [],
        values: [0],
        unit: "",
        source_citation: "",
      },
    ]);
  };

  if (loading) {
    return (
      <div data-testid="analytics-report-artifact-loading">
        <V4Card>
          <div className="flex items-center gap-2 p-4 text-sm text-(--qs-text-3)">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            Loading report artifact…
          </div>
        </V4Card>
      </div>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  if (!snapshot.has_artifact || !snapshot.artifact) {
    return (
      <div data-testid="analytics-report-artifact-empty">
        <V4Card>
          <V4CardHeader
            kicker="DA5 · Report artifact"
            title="No active report"
            description={snapshot.empty_hint}
          />
          <div className="px-4 pb-4">
            <Link href="/apps-tools/analytics?section=question#analytics-question" className="qs-btn qs-btn--primary qs-btn--sm">
              Open Business Question wizard
            </Link>
          </div>
        </V4Card>
      </div>
    );
  }

  const artifact = snapshot.artifact;

  return (
    <div id="analytics-report-artifact" data-testid="analytics-report-artifact">
      <V4Card>
      <V4CardHeader
        kicker="DA5 · Report artifact"
        title={artifact.title}
        description="Session-bound markdown + chart blocks — operator edits version the lineage."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <V4Badge tone="info">v{artifact.version}</V4Badge>
            {artifact.session_status ? (
              <V4Badge tone={artifact.session_status === "completed" ? "ok" : "purple"}>
                {artifact.session_status}
              </V4Badge>
            ) : null}
            <HiveRefreshButton busy={loading} onClick={() => void load()} />
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              onClick={() => setMode((m) => (m === "edit" ? "preview" : "edit"))}
            >
              <Pencil className="h-3.5 w-3.5" aria-hidden />
              {mode === "edit" ? "Preview" : "Edit"}
            </button>
          </div>
        }
      />

      <div className="space-y-4 px-4 pb-4">
        <div className="flex flex-wrap gap-2 text-sm">
          {artifact.task_href ? (
            <Link href={artifact.task_href} className="text-cyan hover:underline">
              Mission task
            </Link>
          ) : null}
          {artifact.session_href ? (
            <>
              {artifact.task_href ? <span className="text-(--qs-text-3)">·</span> : null}
              <Link href={artifact.session_href} className="text-cyan hover:underline">
                Analytics session
              </Link>
            </>
          ) : null}
        </div>

        {mode === "edit" ? (
          <textarea
            className="qs-input min-h-[280px] w-full font-mono text-sm"
            value={markdown}
            onChange={(e) => setMarkdown(e.target.value)}
            data-testid="analytics-report-markdown-editor"
          />
        ) : (
          <MarkdownPreview content={markdown} />
        )}

        <div className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-(--qs-text)">Chart blocks</h3>
            {mode === "edit" ? (
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={addBlock}>
                <Plus className="h-3.5 w-3.5" aria-hidden />
                Add block
              </button>
            ) : null}
          </div>

          {blocks.length === 0 ? (
            <p className="text-sm text-(--qs-text-3)">No chart blocks — add KPI or bar charts in edit mode.</p>
          ) : (
            <div className="grid gap-3 lg:grid-cols-2">
              {blocks.map((block, idx) =>
                mode === "edit" ? (
                  <div key={block.id} className="space-y-2 rounded-lg border border-white/10 p-3">
                    <div className="flex gap-2">
                      <input
                        className="qs-input flex-1 text-sm"
                        value={block.title}
                        onChange={(e) =>
                          setBlocks((prev) =>
                            prev.map((row, i) => (i === idx ? { ...row, title: e.target.value } : row)),
                          )
                        }
                      />
                      <select
                        className="qs-input text-sm"
                        value={block.chart_type}
                        onChange={(e) =>
                          setBlocks((prev) =>
                            prev.map((row, i) =>
                              i === idx ? { ...row, chart_type: e.target.value as ChartType } : row,
                            ),
                          )
                        }
                      >
                        <option value="kpi">KPI</option>
                        <option value="bar">Bar</option>
                        <option value="line">Line</option>
                      </select>
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--sm"
                        aria-label="Remove chart block"
                        onClick={() => setBlocks((prev) => prev.filter((_, i) => i !== idx))}
                      >
                        <Trash2 className="h-3.5 w-3.5" aria-hidden />
                      </button>
                    </div>
                    <input
                      className="qs-input w-full text-xs"
                      placeholder="Values (comma-separated)"
                      value={block.values.join(", ")}
                      onChange={(e) => {
                        const values = e.target.value
                          .split(",")
                          .map((v) => Number.parseFloat(v.trim()))
                          .filter((v) => !Number.isNaN(v));
                        setBlocks((prev) =>
                          prev.map((row, i) => (i === idx ? { ...row, values } : row)),
                        );
                      }}
                    />
                    {block.chart_type !== "kpi" ? (
                      <input
                        className="qs-input w-full text-xs"
                        placeholder="Labels (comma-separated)"
                        value={block.labels.join(", ")}
                        onChange={(e) => {
                          const labels = e.target.value.split(",").map((v) => v.trim()).filter(Boolean);
                          setBlocks((prev) =>
                            prev.map((row, i) => (i === idx ? { ...row, labels } : row)),
                          );
                        }}
                      />
                    ) : (
                      <input
                        className="qs-input w-full text-xs"
                        placeholder="Unit (e.g. users, %)"
                        value={block.unit}
                        onChange={(e) =>
                          setBlocks((prev) =>
                            prev.map((row, i) => (i === idx ? { ...row, unit: e.target.value } : row)),
                          )
                        }
                      />
                    )}
                    <input
                      className="qs-input w-full text-xs"
                      placeholder="Source citation (connector · query · timestamp)"
                      value={block.source_citation}
                      onChange={(e) =>
                        setBlocks((prev) =>
                          prev.map((row, i) => (i === idx ? { ...row, source_citation: e.target.value } : row)),
                        )
                      }
                    />
                  </div>
                ) : (
                  <ChartBlockPreview key={block.id} block={block} />
                ),
              )}
            </div>
          )}
        </div>

        {mode === "edit" ? (
          <button
            type="button"
            className="qs-btn qs-btn--primary"
            disabled={saving}
            onClick={() => void save()}
            data-testid="analytics-report-save"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Save className="h-4 w-4" aria-hidden />}
            Save report
          </button>
        ) : null}
      </div>
      </V4Card>
    </div>
  );
}
