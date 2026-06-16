"use client";

import Link from "next/link";
import { BarChart3, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";

interface JournalTagWinRate {
  tag: string;
  window_days: number;
  entry_count: number;
  win_count: number;
  loss_count: number;
  breakeven_count: number;
  win_rate: number | null;
  repeat_mistake_alert: boolean;
}

interface JournalPatternWindow {
  window_days: number;
  entry_count: number;
  resolved_count: number;
  overall_win_rate: number | null;
  tag_stats: JournalTagWinRate[];
  edge_tags: string[];
  repeat_mistakes: string[];
}

interface JournalPatternStrip {
  enabled: boolean;
  generated_at: string;
  windows: JournalPatternWindow[];
  repeat_mistake_alerts: string[];
  operator_hint: string;
  morning_brief_line: string;
  workspace_href: string;
}

function formatWinRate(value: number | null | undefined): string {
  if (value == null) {
    return "—";
  }
  return `${Math.round(value * 100)}%`;
}

export function JournalStudioPatternStripPanel(): JSX.Element | null {
  const [strip, setStrip] = useState<JournalPatternStrip | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<JournalPatternStrip>("journal-studio/pattern-strip");
      setStrip(data);
    } catch {
      setStrip(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div data-testid="journal-studio-pattern-strip-panel">
        <V4Card className="flex items-center gap-2 p-4 text-sm text-white/60">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading pattern strip…
        </V4Card>
      </div>
    );
  }

  if (!strip?.enabled) {
    return (
      <div data-testid="journal-studio-pattern-strip-panel">
        <V4Card className="p-4 text-sm text-white/60">Pattern strip is disabled.</V4Card>
      </div>
    );
  }

  const window30 = strip.windows.find((row) => row.window_days === 30);
  const window90 = strip.windows.find((row) => row.window_days === 90);

  return (
    <div className="space-y-4" data-testid="journal-studio-pattern-strip-panel">
      <V4Card id="journal-studio-pattern-strip" className="border-amber-500/25">
        <V4CardHeader
          leadingIcon={BarChart3}
          title="30/90-day pattern strip"
          description="Win rate by tag, edge tags from wins, and repeat-mistake alerts before your next session."
          actions={<HiveRefreshButton onClick={() => void load()} aria-label="Refresh pattern strip" />}
        />
        <p className="mt-3 text-sm text-white/70">{strip.operator_hint}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <V4Badge tone="info">30d {formatWinRate(window30?.overall_win_rate)}</V4Badge>
          <V4Badge tone="info">90d {formatWinRate(window90?.overall_win_rate)}</V4Badge>
          {strip.repeat_mistake_alerts.length > 0 ? (
            <V4Badge tone="warn">{strip.repeat_mistake_alerts.length} repeat mistake(s)</V4Badge>
          ) : null}
          <Link href={strip.workspace_href} className="text-xs text-cyan-300 hover:underline">
            Share link
          </Link>
        </div>
      </V4Card>

      {strip.repeat_mistake_alerts.length > 0 ? (
        <div data-testid="journal-pattern-repeat-alerts">
          <V4Card>
            <V4CardHeader
              leadingIcon={BarChart3}
              title="Repeat-mistake alerts"
              description="Tags with ≥2 entries and at least one loss in the last 30 days."
            />
            <ul className="mt-4 flex flex-wrap gap-2">
              {strip.repeat_mistake_alerts.map((tag) => (
                <V4Badge key={tag} tone="warn">
                  {tag}
                </V4Badge>
              ))}
            </ul>
          </V4Card>
        </div>
      ) : null}

      {strip.windows.map((window) => (
        <V4Card key={window.window_days}>
          <V4CardHeader
            leadingIcon={BarChart3}
            title={`${window.window_days}-day window`}
            description={`${window.entry_count} entries · ${window.resolved_count} resolved · win rate ${formatWinRate(window.overall_win_rate)}`}
          />
          {window.tag_stats.length > 0 ? (
            <ul className="mt-4 space-y-3">
              {window.tag_stats.map((row) => (
                <li key={`${window.window_days}-${row.tag}`} className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <V4Badge tone={row.repeat_mistake_alert ? "warn" : "info"}>{row.tag}</V4Badge>
                    <span className="text-xs text-white/50">
                      {row.entry_count} entries · {formatWinRate(row.win_rate)} win rate
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-white/50">
                    {row.win_count}W / {row.loss_count}L / {row.breakeven_count}BE
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-white/60">No tagged entries in this window yet.</p>
          )}
          {window.edge_tags.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="text-xs text-white/50">Edge tags:</span>
              {window.edge_tags.map((tag) => (
                <V4Badge key={`${window.window_days}-edge-${tag}`} tone="ok">
                  {tag}
                </V4Badge>
              ))}
            </div>
          ) : null}
        </V4Card>
      ))}
    </div>
  );
}
