"use client";

import { Download } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import {
  auditActorLabel,
  filterAuditRows,
  formatAuditAction,
  formatAuditTime,
  ipFromAuditPayload,
  type AuditFilter,
  type TenantAuditLogRow,
} from "@/lib/settings-audit-utils";

interface TeamMemberRow {
  user_id: string;
  email: string;
}

interface TeamOverviewResponse {
  members: TeamMemberRow[];
}

export function SettingsAuditPanel() {
  const [rows, setRows] = useState<TenantAuditLogRow[] | null>(null);
  const [memberMap, setMemberMap] = useState<Map<string, string>>(new Map());
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState<AuditFilter>("all");

  const load = useCallback(async () => {
    try {
      const [auditRows, team] = await Promise.all([
        hiveGet<TenantAuditLogRow[]>("settings/team/audit-logs"),
        hiveGet<TeamOverviewResponse>("settings/team").catch(() => ({ members: [] as TeamMemberRow[] })),
      ]);
      setRows(auditRows);
      const map = new Map<string, string>();
      for (const m of team.members ?? []) {
        map.set(m.user_id, m.email);
      }
      setMemberMap(map);
      setErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Load failed";
      setErr(msg);
      setRows([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => filterAuditRows(rows ?? [], filter), [filter, rows]);

  function exportJson(): void {
    if (!filtered.length) {
      toast.message("Nothing to export for the current filter.");
      return;
    }
    const blob = new Blob([JSON.stringify(filtered, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `queenswarm-audit-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Audit log exported.");
  }

  return (
    <V4Card>
      <V4CardHeader
        title="Audit log"
        description="Admin actions, key rotations, hive auto-rebalances · 60-day retention."
        actions={
          <>
            <QsSelect
              className="w-[140px] py-2 text-sm"
              value={filter}
              onValueChange={(next) => setFilter(next as AuditFilter)}
              aria-label="Filter audit actions"
              options={[
                { value: "all", label: "All actions" },
                { value: "auth", label: "Auth" },
                { value: "keys", label: "Keys" },
                { value: "team", label: "Team" },
                { value: "sharing", label: "Sharing" },
              ]}
            />
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1.5" onClick={() => exportJson()}>
              <Download className="h-3.5 w-3.5" aria-hidden />
              Export
            </button>
          </>
        }
      />

      {err ? (
        <p className="mt-4 rounded-xl border border-danger/30 bg-danger/6 px-4 py-3 text-sm text-danger" role="alert">
          {err}
        </p>
      ) : null}

      {!rows ? (
        <div className="mt-4 space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded-xl bg-white/4" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="mt-6 text-sm text-(--qs-text-3)">No audit entries yet for this filter.</p>
      ) : (
        <div className="mt-4">
          {filtered.map((row) => (
            <div key={row.id} className="v4-audit-row">
              <span className="v4-audit-time">{formatAuditTime(row.created_at)}</span>
              <div className="min-w-0 flex-1">
                <span className="v4-audit-who">{auditActorLabel(row, memberMap)}</span>
                <span className="v4-audit-action"> · {formatAuditAction(row)}</span>
              </div>
              <span className="v4-audit-ip">{ipFromAuditPayload(row.payload)}</span>
            </div>
          ))}
        </div>
      )}

      {rows && rows.length > 0 ? (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <V4Badge tone="info">{filtered.length} entries</V4Badge>
          <span className="text-xs text-(--qs-text-3)">Requires team:manage permission</span>
        </div>
      ) : null}
    </V4Card>
  );
}
