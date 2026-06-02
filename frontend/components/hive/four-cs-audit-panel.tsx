"use client";

import { Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { HiveApiError, hiveGet } from "@/lib/api";
import { MANUAL_HREFS } from "@/lib/manual-routes";

interface FourCsDimension {
  id: string;
  label: string;
  score: number;
  status: "ok" | "warn" | "missing";
  signals: string[];
  actions: string[];
}

interface FourCsAuditPayload {
  overall_score: number;
  overall_status: "ok" | "warn" | "missing";
  dimensions: FourCsDimension[];
  maintainer_safety: Array<{ id: string; label: string }>;
}

function statusTone(status: string): "ok" | "warn" | "info" {
  if (status === "ok") return "ok";
  if (status === "warn") return "warn";
  return "info";
}

function FourCsAuditPanelInner(): JSX.Element {
  const [audit, setAudit] = useState<FourCsAuditPayload | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const row = await hiveGet<FourCsAuditPayload>("harness/four-cs-audit");
      setAudit(row);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Four Cs audit unavailable");
      setAudit(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !audit) {
    return (
      <div className="flex min-h-32 items-center justify-center gap-2 text-sm text-(--qs-text-3)">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Running Four Cs audit…
      </div>
    );
  }

  if (!audit) {
    return (
      <V4Card>
        <p className="text-sm text-(--qs-text-3)">Four Cs audit unavailable.</p>
      </V4Card>
    );
  }

  return (
    <V4Card>
      <V4CardHeader
        title="Four Cs readiness"
        description="Context · Connections · Capabilities · Cadence — weekly AI OS health (Nate Herk framework)."
        hint={sectionHintNode("harnessFourCs")}
        actions={
          <div className="flex items-center gap-2">
            <V4Badge tone={statusTone(audit.overall_status)}>{audit.overall_score}/100</V4Badge>
            <HiveRefreshButton onClick={() => void load()} busy={loading} label="Refresh audit" />
          </div>
        }
      />
      <p className="mb-4 text-xs text-(--qs-text-3)">
        Read-only score — no auto-changes.{" "}
        <Link href={MANUAL_HREFS.manualHarnessFourCs} className="text-cyan underline-offset-2 hover:underline">
          Manual → Four Cs
        </Link>
      </p>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {audit.dimensions.map((dim) => (
          <article
            key={dim.id}
            className="rounded-xl border border-(--qs-border)/50 bg-black/20 p-4"
          >
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-(--qs-text)">{dim.label}</h3>
              <V4Badge tone={statusTone(dim.status)}>{dim.score}</V4Badge>
            </div>
            <ul className="mt-2 space-y-1 text-xs text-(--qs-text-2)">
              {dim.signals.map((s) => (
                <li key={s}>✓ {s}</li>
              ))}
            </ul>
            {dim.actions.length ? (
              <ul className="mt-2 space-y-1 text-xs text-pollen">
                {dim.actions.map((a) => (
                  <li key={a}>→ {a}</li>
                ))}
              </ul>
            ) : null}
          </article>
        ))}
      </div>
      <details className="mt-5 rounded-lg border border-(--qs-border)/40 p-3">
        <summary className="cursor-pointer text-xs font-medium text-(--qs-text-2)">
          Queen Maintainer pre-tool safety ({audit.maintainer_safety.length} rules)
        </summary>
        <ul className="mt-2 space-y-1 text-xs text-(--qs-text-3)">
          {audit.maintainer_safety.map((row) => (
            <li key={row.id}>{row.label}</li>
          ))}
        </ul>
      </details>
    </V4Card>
  );
}

export const FourCsAuditPanel = memo(FourCsAuditPanelInner);
