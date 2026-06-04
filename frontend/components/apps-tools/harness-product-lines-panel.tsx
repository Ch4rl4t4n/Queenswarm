"use client";

import { Loader2Icon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import type { HarnessProductCatalog } from "@/lib/hive-types";

function eur(cents: number): string {
  return `€${(cents / 100).toFixed(2)}`;
}

function stars(n: number): string {
  return "⭐".repeat(Math.min(n, 3));
}

export function HarnessProductLinesPanel(): JSX.Element {
  const [catalog, setCatalog] = useState<HarnessProductCatalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await hiveGet<HarnessProductCatalog>("harness-products/catalog");
      setCatalog(data);
    } catch (e) {
      setError(e instanceof HiveApiError ? e.message : "Catalog unavailable.");
      setCatalog(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <V4Card className="mt-4">
        <div className="flex items-center gap-2 px-4 py-6 text-sm text-(--qs-text-3)">
          <Loader2Icon className="size-4 animate-spin" aria-hidden />
          Loading product lines…
        </div>
      </V4Card>
    );
  }

  if (error || !catalog) {
    return (
      <V4Card className="mt-4">
        <p className="px-4 py-4 text-xs text-error">{error ?? "No catalog data."}</p>
      </V4Card>
    );
  }

  const scenarios = catalog.revenue_scenarios;

  return (
    <V4Card className="mt-4">
      <V4CardHeader
        title="4× ⭐⭐⭐ product lines"
        description="Cena = čo zaplatí kupujúci na Gumroad. Náš náklad = LLM + hosting pri predaji. Zisk = net po poplatkoch mínus náklad."
      />
      <p className="mt-2 px-4 text-xs text-(--qs-text-3)">{catalog.economics_note}</p>

      <ul className="mt-4 space-y-4 px-4 pb-4">
        {catalog.lines.map((line) => (
          <li key={line.id} className="rounded-xl border border-(--qs-border-2) bg-(--qs-surface-2)/40 px-3 py-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-sm font-medium">
                  {stars(line.stars)} {line.title}
                </p>
                <p className="mt-1 text-xs text-(--qs-text-3)">{line.summary}</p>
              </div>
              <V4Badge tone={line.status === "live" ? "ok" : "info"}>{line.status}</V4Badge>
            </div>
            <dl className="mt-3 grid gap-1 text-[11px] text-(--qs-text-3) sm:grid-cols-2">
              <div>
                <dt className="text-(--qs-text-4)">Odporúčaná cena (Gumroad)</dt>
                <dd className="font-mono text-pollen">
                  {eur(line.economics.price_eur_cents_recommended)}{" "}
                  <span className="text-(--qs-text-4)">
                    ({eur(line.economics.price_eur_cents_min)}–{eur(line.economics.price_eur_cents_max)})
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-(--qs-text-4)">Náš náklad / predaj</dt>
                <dd className="font-mono">{eur(line.economics.our_cost_eur_cents_per_sale)}</dd>
              </div>
              <div>
                <dt className="text-(--qs-text-4)">Jednorazový setup (factory)</dt>
                <dd className="font-mono">{eur(line.economics.our_cost_eur_cents_one_time_setup)}</dd>
              </div>
              <div>
                <dt className="text-(--qs-text-4)">Tvoj čistý zisk / predaj</dt>
                <dd className="font-mono text-success">
                  {eur(line.economics.net_eur_cents_per_sale)} ({line.economics.margin_pct}% marža)
                </dd>
              </div>
            </dl>
            <p className="mt-2 text-[10px] text-(--qs-text-4)">{line.gumroad_angle}</p>
          </li>
        ))}
      </ul>

      <div className="border-t border-(--qs-border-2) px-4 py-4">
        <p className="text-xs font-medium text-(--qs-text-2)">Scenáre mesačného čistého príjmu (orientačné)</p>
        <ul className="mt-2 space-y-2 text-[11px] text-(--qs-text-3)">
          {Object.entries(scenarios).map(([key, row]) => (
            <li key={key} className="flex flex-wrap items-baseline justify-between gap-2">
              <span>
                {key.replace(/_/g, " ")} — eval {row.eval_sales} · kit {row.kit_sales} · runbook {row.runbook_sales}
              </span>
              <span className="font-mono text-pollen">~€{row.label_eur_net}/mes</span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-[10px] text-(--qs-text-4)">
          Príklad: pri €29 predaji Gumroad po poplatkoch (~13 %) dostaneš ~€25. Náš LLM eval stojí ~€0,08 → čistý
          zisk ~€24,92 na predaj. Setup kitu (~€0,78) platíš raz pri vytvorení, nie pri každom predaji.
        </p>
      </div>
    </V4Card>
  );
}
