import type { SpendDayDatum } from "@/components/hive/spend-trend-chart";
import type { OperatorCostSummary } from "@/lib/hive-types";

/** Consolidate ledger rows after multi-model splits into one daily tally. */
export function consolidateDailySpend(series: OperatorCostSummary["series"]): SpendDayDatum[] {
  const map = new Map<string, number>();
  for (const row of series) {
    map.set(row.day, (map.get(row.day) ?? 0) + row.spend_usd);
  }
  return [...map.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([day, spend_usd]) => ({ day, spend_usd }));
}

export interface ProviderSpendAgg {
  model: string;
  spend_usd: number;
}

/** Aggregate by provider label inside the sliding window (operator ledger). */
export function aggregateSpendByModel(series: OperatorCostSummary["series"]): ProviderSpendAgg[] {
  const map = new Map<string, number>();
  for (const row of series) {
    map.set(row.model, (map.get(row.model) ?? 0) + row.spend_usd);
  }
  return [...map.entries()].map(([model, spend_usd]) => ({ model, spend_usd }));
}
