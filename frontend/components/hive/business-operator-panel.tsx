"use client";

import Link from "next/link";
import { Briefcase, ExternalLink, Loader2, Target } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";

import { BusinessApprovalInbox } from "@/components/hive/business-approval-inbox";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader, type V4BadgeTone } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

interface BusinessAction {
  id: string;
  lane: string;
  title: string;
  detail: string;
  priority: "high" | "medium" | "low";
  href: string | null;
}

interface BusinessOperatorSnapshot {
  enabled: boolean;
  generated_at: string;
  headline?: string;
  tagline: string;
  catalog: {
    product_count: number;
    featured_count: number;
    gumroad_linked_count: number;
    marketing_origin: string;
  };
  revenue: {
    ready_summary?: string;
    scorecard_ready_count?: number | null;
    first_upload_candidate?: string | null;
    next_operator_action?: string;
    missing_reports?: string[];
  };
  missions: {
    triage_count: number;
    ready_count: number;
    in_progress_count: number;
    blocked_count: number;
  };
  top_actions: BusinessAction[];
  links: Record<string, string>;
}

function priorityTone(priority: BusinessAction["priority"]): V4BadgeTone {
  if (priority === "high") {
    return "gold";
  }
  if (priority === "medium") {
    return "info";
  }
  return "warn";
}

function BusinessOperatorPanelInner(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<BusinessOperatorSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<BusinessOperatorSnapshot>("operator/business/snapshot");
      setSnapshot(data);
      setError(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Business operator unavailable";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !snapshot) {
    return (
      <V4Card className="mb-4 border-pollen/30">
        <div className="flex items-center gap-2 p-4 text-sm text-(--qs-muted)">
          <Loader2 className="size-4 animate-spin text-pollen" aria-hidden />
          Loading business brief…
        </div>
      </V4Card>
    );
  }

  if (error && !snapshot) {
    return (
      <V4Card className="mb-4 border-error/30">
        <p className="p-4 text-sm text-error">{error}</p>
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  const marketingHref = snapshot.links.marketing_skills ?? "https://letagentscook.org/skills";
  const isExternal = (href: string): boolean => href.startsWith("http");

  return (
    <V4Card className="mb-4 border-pollen/35 bg-pollen/5" id="business-operator">
      <V4CardHeader
        kicker="Chief Business Operator"
        title={snapshot.headline?.trim() || "What to do for the business"}
        description={snapshot.tagline}
        actions={<HiveRefreshButton busy={loading} onClick={() => void load()} />}
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-(--qs-border) bg-(--qs-surface-2) p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-muted)">Catalog live</p>
          <p className="mt-1 font-[family-name:var(--font-hive-mono)] text-2xl font-bold text-pollen">
            {snapshot.catalog.product_count}
          </p>
          <p className="mt-1 text-xs text-(--qs-text-2)">
            {snapshot.catalog.gumroad_linked_count} with Gumroad URL
          </p>
        </div>
        <div className="rounded-lg border border-(--qs-border) bg-(--qs-surface-2) p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-muted)">Scorecard ready</p>
          <p className="mt-1 font-[family-name:var(--font-hive-mono)] text-2xl font-bold text-cyan">
            {snapshot.revenue.scorecard_ready_count ?? "—"}
          </p>
          <p className="mt-1 text-xs text-(--qs-text-2)">{snapshot.revenue.ready_summary ?? "—"}</p>
        </div>
        <div className="rounded-lg border border-(--qs-border) bg-(--qs-surface-2) p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-muted)">Mission queue</p>
          <p className="mt-1 font-[family-name:var(--font-hive-mono)] text-2xl font-bold text-(--qs-text)">
            {snapshot.missions.triage_count}
          </p>
          <p className="mt-1 text-xs text-(--qs-text-2)">triage · {snapshot.missions.in_progress_count} in progress</p>
        </div>
      </div>

      <BusinessApprovalInbox />

      <div className="mb-4">
        <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-pollen">
          <Target className="size-3.5" aria-hidden />
          Top 3 actions
        </p>
        <ul className="space-y-2">
          {snapshot.top_actions.map((action) => {
            const tone = priorityTone(action.priority);
            const content = (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <V4Badge tone={tone}>{action.priority}</V4Badge>
                  <span className="text-[10px] uppercase tracking-wider text-(--qs-muted)">{action.lane}</span>
                </div>
                <p className="mt-1 font-medium text-(--qs-text)">{action.title}</p>
                <p className="mt-0.5 text-xs text-(--qs-text-2)">{action.detail}</p>
              </>
            );
            const className = cn(
              "block rounded-lg border border-(--qs-border) bg-(--qs-surface) p-3 transition-colors",
              action.href && "hover:border-pollen/40",
            );
            if (!action.href) {
              return (
                <li key={action.id} className={className}>
                  {content}
                </li>
              );
            }
            if (isExternal(action.href)) {
              return (
                <li key={action.id}>
                  <a href={action.href} className={className} target="_blank" rel="noopener noreferrer">
                    {content}
                  </a>
                </li>
              );
            }
            return (
              <li key={action.id}>
                <Link href={action.href} className={className}>
                  {content}
                </Link>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="flex flex-wrap gap-2">
        <Link href="/agents#sessions" className="qs-btn qs-btn--primary qs-btn--sm gap-1">
          <Briefcase className="size-4" aria-hidden />
          Agents → Sessions
        </Link>
        <Link href="/tasks" className="qs-btn qs-btn--ghost qs-btn--sm gap-1">
          <Briefcase className="size-4" aria-hidden />
          Mission Control
        </Link>
        <a
          href={marketingHref}
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
          target="_blank"
          rel="noopener noreferrer"
        >
          <ExternalLink className="size-4" aria-hidden />
          letagentscook.org/skills
        </a>
        <Link href="/factory" className="qs-btn qs-btn--ghost qs-btn--sm">
          Factory queue
        </Link>
      </div>
    </V4Card>
  );
}

export const BusinessOperatorPanel = memo(BusinessOperatorPanelInner);
BusinessOperatorPanel.displayName = "BusinessOperatorPanel";
