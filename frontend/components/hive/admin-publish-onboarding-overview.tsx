"use client";

import { Loader2 } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";

interface PublishOnboardingTenantRow {
  tenant_id: string;
  tenant_slug: string;
  tenant_name: string;
  progress_pct: number;
  steps_done: number;
  steps_total: number;
}

interface PublishOnboardingAdminOverview {
  generated_at: string;
  tenant_count: number;
  average_progress_pct: number;
  tenants: PublishOnboardingTenantRow[];
}

function AdminPublishOnboardingOverviewInner() {
  const [overview, setOverview] = useState<PublishOnboardingAdminOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<PublishOnboardingAdminOverview>("admin/publish-lane/onboarding-overview");
      setOverview(data);
      setErr(null);
    } catch (exc) {
      setErr(exc instanceof HiveApiError ? exc.message : "Overview unavailable");
      setOverview(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <V4Card className="p-4">
        <p className="flex items-center gap-2 text-sm text-(--qs-muted)">
          <Loader2 className="size-4 animate-spin" aria-hidden /> Loading publish lane progress…
        </p>
      </V4Card>
    );
  }

  if (err || !overview) {
    return null;
  }

  return (
    <V4Card className="p-4 md:p-5">
      <V4CardHeader
        as="h2"
        kicker="Publish lane"
        title="Multi-tenant onboarding"
        description={`Priemer ${overview.average_progress_pct}% · ${overview.tenant_count} tenant(s)`}
      />
      <div className="mb-3 h-2 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-pollen"
          style={{ width: `${overview.average_progress_pct}%` }}
          role="progressbar"
          aria-valuenow={overview.average_progress_pct}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      <ul className="max-h-64 space-y-2 overflow-auto">
        {overview.tenants.map((row) => (
          <li
            key={row.tenant_id}
            className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-sm"
          >
            <div>
              <p className="font-semibold text-(--qs-text)">{row.tenant_name}</p>
              <p className="font-mono text-[10px] text-(--qs-muted)">{row.tenant_slug}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-cyan">
                {row.steps_done}/{row.steps_total}
              </span>
              <V4Badge tone={row.progress_pct >= 100 ? "ok" : row.progress_pct >= 50 ? "gold" : "info"}>
                {row.progress_pct}%
              </V4Badge>
            </div>
          </li>
        ))}
      </ul>
    </V4Card>
  );
}

export const AdminPublishOnboardingOverview = memo(AdminPublishOnboardingOverviewInner);
AdminPublishOnboardingOverview.displayName = "AdminPublishOnboardingOverview";
