"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useState } from "react";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";

interface RecipeMarketplaceBetaSnapshot {
  enabled: boolean;
  approved_count: number;
  pending_count: number;
  total_listings: number;
  config: Record<string, unknown>;
}

function RecipeMarketplaceBetaPanelInner(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<RecipeMarketplaceBetaSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<RecipeMarketplaceBetaSnapshot>("recipes/marketplace-beta");
      setSnapshot(data);
    } catch (err) {
      if (err instanceof HiveApiError && err.status === 404) {
        setSnapshot(null);
        return;
      }
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
      <V4Card className="p-4">
        <p className="flex items-center gap-2 text-sm text-(--qs-muted)">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading marketplace beta…
        </p>
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  const cutPct = snapshot.config.creator_cut_pct ?? snapshot.config.cut_pct;

  return (
    <V4Card className="p-4 md:p-5">
      <V4CardHeader
        as="h2"
        kicker="Marketplace beta"
        title="UGC recipe listings"
        description="Verified trading & marketing recipes with curator review and revenue share."
      />
      <div className="mt-3 flex flex-wrap gap-2">
        <V4Badge tone="ok">{snapshot.approved_count} approved</V4Badge>
        <V4Badge tone="gold">{snapshot.pending_count} pending</V4Badge>
        <V4Badge tone="info">{snapshot.total_listings} total</V4Badge>
        {typeof cutPct === "number" ? (
          <V4Badge tone="info">Creator cut {cutPct}%</V4Badge>
        ) : null}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Link href="/integrations?tab=marketplace" className="qs-btn qs-btn--ghost qs-btn--sm">
          Submit listing
        </Link>
        <Link href="/settings/harness" className="qs-btn qs-btn--ghost qs-btn--sm">
          Operator hub
        </Link>
      </div>
    </V4Card>
  );
}

export const RecipeMarketplaceBetaPanel = memo(RecipeMarketplaceBetaPanelInner);
RecipeMarketplaceBetaPanel.displayName = "RecipeMarketplaceBetaPanel";
