"use client";

import Link from "next/link";
import { Brain, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";

interface PreTradeMistake {
  tag: string;
  count: number;
  latest_lesson: string;
}

interface PreTradeRecall {
  enabled: boolean;
  window_days: number;
  mistake_count: number;
  top_mistakes: PreTradeMistake[];
  edge_reminders: string[];
  thesis_title: string | null;
  thesis_snippet: string;
  operator_hint: string;
  thesis_wizard_href: string;
  cockpit_href: string;
}

export function JournalStudioPretradeRecallPanel(): JSX.Element | null {
  const [recall, setRecall] = useState<PreTradeRecall | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<PreTradeRecall>("journal-studio/pretrade-recall?window_days=30");
      setRecall(data);
    } catch {
      setRecall(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div data-testid="journal-studio-pretrade-recall-panel">
        <V4Card className="flex items-center gap-2 p-4 text-sm text-white/60">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading pre-trade recall…
        </V4Card>
      </div>
    );
  }

  if (!recall?.enabled) {
    return (
      <div data-testid="journal-studio-pretrade-recall-panel">
        <V4Card className="p-4 text-sm text-white/60">Pre-trade recall is disabled.</V4Card>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="journal-studio-pretrade-recall-panel">
      <V4Card id="journal-studio-pretrade-recall" className="border-cyan-500/25">
        <V4CardHeader
          leadingIcon={Brain}
          title="Pre-trade recall"
          description="Top mistakes, NP5 thesis, and wiki edges injected before your next trading session."
          actions={<HiveRefreshButton onClick={() => void load()} aria-label="Refresh pre-trade recall" />}
        />
        <p className="mt-3 text-sm text-white/70">{recall.operator_hint}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <V4Badge tone="warn">{recall.mistake_count} mistake patterns</V4Badge>
          <V4Badge tone="info">{recall.window_days}d window</V4Badge>
          <Link href={recall.cockpit_href} className="text-xs text-cyan-300 hover:underline">
            Open trading cockpit
          </Link>
          <Link href={recall.thesis_wizard_href} className="text-xs text-amber-300 hover:underline">
            NP5 thesis brief
          </Link>
        </div>
      </V4Card>

      {recall.top_mistakes.length > 0 ? (
        <V4Card>
          <V4CardHeader leadingIcon={Brain} title="Top mistakes" description="Slow down if these apply today." />
          <ul className="mt-4 space-y-3">
            {recall.top_mistakes.map((row) => (
              <li key={row.tag} className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <V4Badge tone="warn">{row.tag}</V4Badge>
                  <span className="text-xs text-white/50">{row.count}× in window</span>
                </div>
                {row.latest_lesson ? <p className="mt-2 text-sm text-white/70">{row.latest_lesson}</p> : null}
              </li>
            ))}
          </ul>
        </V4Card>
      ) : null}

      {recall.thesis_snippet ? (
        <div data-testid="journal-pretrade-thesis-strip">
          <V4Card>
            <V4CardHeader leadingIcon={Brain} title={recall.thesis_title ?? "Thesis brief"} description="NP5 kill criteria reminder" />
            <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap text-xs text-white/70">{recall.thesis_snippet}</pre>
          </V4Card>
        </div>
      ) : null}

      {recall.edge_reminders.length > 0 ? (
        <V4Card>
          <V4CardHeader leadingIcon={Brain} title="Edge reminders" description="Patterns from recent verified entries" />
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-white/70">
            {recall.edge_reminders.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </V4Card>
      ) : null}
    </div>
  );
}
