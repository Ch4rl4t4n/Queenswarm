"use client";

import { GitBranch, Loader2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";

interface LineageRow {
  section_id: string;
  section_label: string;
  connector: string;
  connector_label: string;
  query: string;
  fetched_at: string;
  bound_to: string;
  verified: boolean;
  detail: string;
}

interface LineageSnapshot {
  enabled: boolean;
  has_rows: boolean;
  deliverable_id: string | null;
  deliverable_version: number | null;
  report_title: string | null;
  rows: LineageRow[];
  verified_count: number;
  gap_count: number;
  empty_hint: string;
}

export function AnalyticsDataLineagePanel(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<LineageSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<LineageSnapshot>("analytics-workspace/data-lineage");
      setSnapshot(data);
    } catch {
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <V4Card data-testid="analytics-data-lineage-loading">
        <div className="flex items-center gap-2 p-4 text-sm text-(--qs-text-3)">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Loading data lineage…
        </div>
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  if (!snapshot.has_rows) {
    return (
      <V4Card data-testid="analytics-data-lineage-empty">
        <V4CardHeader
          kicker="DA6 · Data lineage"
          title="No lineage rows yet"
          description={snapshot.empty_hint}
        />
        <div className="px-4 pb-4">
          <Link href="/apps-tools/analytics?section=question#analytics-question" className="qs-btn qs-btn--primary qs-btn--sm">
            Dispatch business question
          </Link>
        </div>
      </V4Card>
    );
  }

  return (
    <V4Card id="analytics-data-lineage" data-testid="analytics-data-lineage">
      <V4CardHeader
        kicker="DA6 · Data lineage"
        title={snapshot.report_title ?? "Report lineage"}
        description="Connector · query · timestamp per chart block and narrative section."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {snapshot.deliverable_version ? (
              <V4Badge tone="info">v{snapshot.deliverable_version}</V4Badge>
            ) : null}
            <V4Badge tone="ok">{snapshot.verified_count} verified</V4Badge>
            {snapshot.gap_count > 0 ? (
              <V4Badge tone="warn">{snapshot.gap_count} gaps</V4Badge>
            ) : null}
            <HiveRefreshButton busy={loading} onClick={() => void load()} />
          </div>
        }
      />

      <div className="overflow-x-auto px-4 pb-4">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b border-white/10 text-xs uppercase tracking-wide text-(--qs-text-3)">
              <th className="py-2 pr-3 font-medium">Section</th>
              <th className="py-2 pr-3 font-medium">Connector</th>
              <th className="py-2 pr-3 font-medium">Query</th>
              <th className="py-2 pr-3 font-medium">Fetched</th>
              <th className="py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {snapshot.rows.map((row) => (
              <tr
                key={`${row.bound_to}-${row.section_id}`}
                className="border-b border-white/5 align-top"
                data-testid={`analytics-lineage-row-${row.section_id}`}
              >
                <td className="py-3 pr-3">
                  <div className="font-medium text-(--qs-text)">{row.section_label}</div>
                  <div className="mt-0.5 text-xs text-(--qs-text-3)">{row.bound_to}</div>
                </td>
                <td className="py-3 pr-3">
                  <span className="inline-flex items-center gap-1 text-cyan">
                    <GitBranch className="h-3.5 w-3.5 shrink-0" aria-hidden />
                    {row.connector_label || row.connector || "—"}
                  </span>
                </td>
                <td className="py-3 pr-3 font-mono text-xs text-(--qs-text-2)">{row.query || "—"}</td>
                <td className="py-3 pr-3 font-mono text-xs text-(--qs-text-2)">{row.fetched_at || "—"}</td>
                <td className="py-3">
                  <V4Badge tone={row.verified ? "ok" : "warn"}>{row.verified ? "verified" : "gap"}</V4Badge>
                  {row.detail ? (
                    <p className="mt-1 max-w-xs text-xs text-(--qs-text-3)">{row.detail}</p>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {snapshot.deliverable_id ? (
        <p className="px-4 pb-4 text-xs text-(--qs-text-3)">
          Bound to deliverable{" "}
          <Link href="/apps-tools/analytics?section=report#analytics-report" className="text-cyan hover:underline">
            {snapshot.deliverable_id.slice(0, 8)}…
          </Link>
          {" · "}
          edit chart citations in Report tab to close gaps.
        </p>
      ) : null}
    </V4Card>
  );
}
