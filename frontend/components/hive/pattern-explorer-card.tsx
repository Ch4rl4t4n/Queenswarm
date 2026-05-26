"use client";

import Link from "next/link";
import { ExternalLink, Loader2Icon, Sparkles } from "lucide-react";

import { CollapsibleLazyPanel } from "@/components/hive/collapsible-lazy-panel";
import { PatternOnboardingBanner } from "@/components/hive/pattern-onboarding-banner";
import { usePlatform } from "@/components/hive/platform-context";
import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { usePatternExplorerData } from "@/lib/hooks/use-pattern-explorer";
import type {
  PatternCatalogRow,
  PatternExplorerPayload,
  PatternExplorerSessionRow,
} from "@/lib/hive-types";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";

function patternTone(count: number): "ok" | "info" | "warn" {
  if (count >= 3) {
    return "ok";
  }
  if (count >= 1) {
    return "info";
  }
  return "warn";
}

function sessionStatusTone(status: string): "ok" | "info" | "warn" | "err" {
  const normalized = status.trim().toLowerCase();
  if (normalized === "completed" || normalized === "approved") {
    return "ok";
  }
  if (normalized === "running") {
    return "info";
  }
  if (normalized === "needs_input") {
    return "warn";
  }
  if (normalized === "failed" || normalized === "rejected") {
    return "err";
  }
  return "info";
}

function PatternCatalogMarketCard({ row }: { row: PatternCatalogRow }): JSX.Element {
  return (
    <article className="v4-dream-cycle-card flex h-full flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-semibold text-(--qs-text)">
            #{row.number} {row.label}
          </p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">Pattern catalog</p>
        </div>
        <V4Badge tone="info">#{row.number}</V4Badge>
      </div>

      <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-3 py-2">
        <p className="v4-field-label text-[10px] text-cyan-300/90">How agents use this</p>
        <p className="mt-1 text-xs leading-relaxed text-(--qs-text-2)">{row.summary}</p>
      </div>

      <p className="font-mono text-[11px] text-(--qs-text-3)">{row.id}</p>
    </article>
  );
}

function PatternSessionMarketCard({ session }: { session: PatternExplorerSessionRow }): JSX.Element {
  const sessionHref = `/agents?session=${encodeURIComponent(session.session_id)}`;
  const startedLabel = session.started_at
    ? new Date(session.started_at).toLocaleString("en-GB", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Recent session";

  return (
    <article className="v4-dream-cycle-card flex h-full flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <p className="line-clamp-2 text-sm font-semibold text-(--qs-text)">
            {session.goal_preview || `Session ${session.session_id.slice(0, 8)}`}
          </p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">{startedLabel}</p>
        </div>
        <V4Badge tone={sessionStatusTone(session.status)}>{session.status}</V4Badge>
      </div>

      {session.goal_preview ? (
        <p className="line-clamp-3 text-xs leading-relaxed text-(--qs-text-3)">{session.goal_preview}</p>
      ) : null}

      <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-3 py-2">
        <p className="v4-field-label text-[10px] text-cyan-300/90">Pattern router selection</p>
        <p className="mt-1 text-xs leading-relaxed text-(--qs-text-2)">
          Primary: {session.primary.length ? session.primary.join(", ") : "—"}
        </p>
        {session.secondary.length ? (
          <p className="mt-1 text-xs text-(--qs-text-3)">Secondary: {session.secondary.join(", ")}</p>
        ) : null}
        {session.rationale[0] ? (
          <p className="mt-2 text-xs text-(--qs-text-3)">Why: {session.rationale[0]}</p>
        ) : null}
      </div>

      <p className="font-mono text-[11px] text-(--qs-text-3)">{session.session_id.slice(0, 8)}…</p>

      <div className="flex flex-wrap gap-2">
        {session.primary.slice(0, 3).map((label) => (
          <V4Badge key={label} tone="gold">
            {label}
          </V4Badge>
        ))}
        {session.forced_reflection ? <V4Badge tone="info">reflection</V4Badge> : null}
      </div>

      <div className="mt-auto flex flex-wrap gap-1.5">
        <Link href={sessionHref} className="qs-btn qs-btn--primary qs-btn--sm gap-1">
          Open session
        </Link>
        <Link
          href={sessionHref}
          className="inline-flex items-center gap-1 text-xs text-pollen hover:underline"
        >
          <ExternalLink className="h-3.5 w-3.5" aria-hidden />
          Supervisor lane
        </Link>
      </div>
    </article>
  );
}

function PatternCatalogGrid({ catalog }: { catalog: PatternCatalogRow[] }): JSX.Element {
  const pageSize = useGridTwoRowPageSize({ columns: 2 });
  const catalogPagination = usePaginatedSlice(catalog, pageSize, `catalog|${pageSize}|${catalog.length}`);

  return (
    <ViewportBoundedPanel
      className="v4-recipe-catalog-panel"
      footer={
        <ListPaginator
          page={catalogPagination.page}
          totalPages={catalogPagination.totalPages}
          totalItems={catalogPagination.totalItems}
          pageSize={pageSize}
          onPageChange={catalogPagination.setPage}
        />
      }
    >
      <div className="grid gap-3 md:grid-cols-2">
        {catalogPagination.slice.map((row) => (
          <PatternCatalogMarketCard key={row.id} row={row} />
        ))}
      </div>
    </ViewportBoundedPanel>
  );
}

function PatternRecentSessionsGrid({ sessions }: { sessions: PatternExplorerSessionRow[] }): JSX.Element {
  const pageSize = useGridTwoRowPageSize({ columns: 2 });
  const sessionsPagination = usePaginatedSlice(sessions, pageSize, `sessions|${pageSize}|${sessions.length}`);

  if (sessions.length === 0) {
    return <p className="text-sm text-(--qs-text-3)">No patterned sessions yet — run a supervisor task.</p>;
  }

  return (
    <ViewportBoundedPanel
      className="v4-recipe-catalog-panel"
      footer={
        <ListPaginator
          page={sessionsPagination.page}
          totalPages={sessionsPagination.totalPages}
          totalItems={sessionsPagination.totalItems}
          pageSize={pageSize}
          onPageChange={sessionsPagination.setPage}
        />
      }
    >
      <div className="grid gap-3 md:grid-cols-2">
        {sessionsPagination.slice.map((session) => (
          <PatternSessionMarketCard key={session.session_id} session={session} />
        ))}
      </div>
    </ViewportBoundedPanel>
  );
}

function PatternExplorerBody({
  data,
  compact,
}: {
  data: PatternExplorerPayload;
  compact?: boolean;
}): JSX.Element {
  const headline =
    data.unique_patterns_today > 0
      ? `Your swarm used ${data.unique_patterns_today} pattern${data.unique_patterns_today === 1 ? "" : "s"} today`
      : "Pattern Router ready — run a supervisor task to see patterns";

  if (compact) {
    return (
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <Sparkles className="h-4 w-4 text-cyan" aria-hidden />
          <span className="text-(--qs-text-2)">{headline}</span>
          {data.router_enabled ? <V4Badge tone="ok">Router on</V4Badge> : <V4Badge tone="warn">Router off</V4Badge>}
          {data.forced_reflection_enabled ? <V4Badge tone="info">Reflection</V4Badge> : null}
        </div>

        {data.usage_today.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {data.usage_today.map((row) => (
              <V4Badge key={row.id} tone={patternTone(row.count)}>
                {row.label} ×{row.count}
              </V4Badge>
            ))}
          </div>
        ) : (
          <p className="text-sm text-(--qs-text-3)">
            No patterned sessions in the last {data.window_hours}h — start a Queen mission or routine.
          </p>
        )}

        {data.recent_sessions.slice(0, 1).map((session) => (
          <PatternSessionMarketCard key={session.session_id} session={session} />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <Sparkles className="h-4 w-4 text-cyan" aria-hidden />
        <span className="text-(--qs-text-2)">{headline}</span>
        {data.router_enabled ? <V4Badge tone="ok">Router on</V4Badge> : <V4Badge tone="warn">Router off</V4Badge>}
        {data.forced_reflection_enabled ? <V4Badge tone="info">Reflection</V4Badge> : null}
        <V4Badge tone="info">{data.sessions_in_window} sessions · {data.window_hours}h</V4Badge>
      </div>

      {data.usage_today.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {data.usage_today.map((row) => (
            <V4Badge key={row.id} tone={patternTone(row.count)}>
              {row.label} ×{row.count}
            </V4Badge>
          ))}
        </div>
      ) : (
        <p className="text-sm text-(--qs-text-3)">
          No patterned sessions in the last {data.window_hours}h — start a Queen mission or routine.
        </p>
      )}

      <CollapsibleLazyPanel
        id="pattern-catalog"
        hashKey="pattern-catalog"
        title="Pattern catalog"
        hint="19 agentic design patterns"
        meta={`${data.catalog.length} patterns`}
        variant="embedded"
        className="qs-bubble qs-bubble--tint-cyan"
        panelClassName="pt-3"
        lazyContent={() => <PatternCatalogGrid catalog={data.catalog} />}
      />

      <CollapsibleLazyPanel
        id="pattern-recent-sessions"
        hashKey="pattern-sessions"
        title="Recent patterned sessions"
        hint="Supervisor missions with Pattern Router selections."
        meta={`${data.recent_sessions.length} sessions`}
        variant="embedded"
        className="qs-bubble qs-bubble--tint-cyan"
        panelClassName="pt-3"
        lazyContent={() => <PatternRecentSessionsGrid sessions={data.recent_sessions} />}
      />
    </div>
  );
}

function PatternExplorerCardInner({
  loading,
  err,
  data,
  compact,
}: {
  loading: boolean;
  err: string | null;
  data: PatternExplorerPayload | null;
  compact?: boolean;
}): JSX.Element {
  return (
    <V4Card className="v4-card-interactive border-cyan/20">
      <V4CardHeader
        title="Pattern Explorer"
        description="Agentic design patterns selected by the hive — transparent orchestration."
        actions={
          <Link href="/settings/harness" className="text-xs text-cyan underline-offset-2 hover:underline">
            Full catalog
          </Link>
        }
      />

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading patterns…
        </p>
      ) : null}

      {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

      {!loading && !err && data ? <PatternExplorerBody data={data} compact={compact} /> : null}
    </V4Card>
  );
}

/** Dashboard — single fetch for onboarding banner + explorer card. */
export function PatternExplorerSection(): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const { loading, err, data } = usePatternExplorerData(true);

  if (!hasFeature("pattern_explorer")) {
    return null;
  }

  return (
    <>
      {!loading && !err && data ? <PatternOnboardingBanner data={data} /> : null}
      <PatternExplorerCardInner loading={loading} err={err} data={data} compact />
    </>
  );
}

/** @deprecated Use PatternExplorerSection on dashboard — kept for direct imports. */
export function PatternExplorerCard(): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const { loading, err, data } = usePatternExplorerData(true);

  if (!hasFeature("pattern_explorer")) {
    return null;
  }

  return <PatternExplorerCardInner loading={loading} err={err} data={data} compact />;
}

/** Settings harness page — full 19-pattern catalog + recent sessions. */
export function PatternExplorerSettingsPanel(): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const { loading, err, data } = usePatternExplorerData(false);

  if (!hasFeature("pattern_explorer")) {
    return <p className="text-sm text-(--qs-text-3)">Pattern Explorer is not enabled for this workspace.</p>;
  }

  if (loading) {
    return (
      <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
        <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading pattern catalog…
      </p>
    );
  }

  if (err || !data) {
    return <p className="text-sm text-(--qs-red)">{err ?? "Pattern Explorer unavailable."}</p>;
  }

  return (
    <V4Card>
      <V4CardHeader
        title="19 agentic design patterns"
        description="Heuristic Pattern Router selects primary + secondary patterns at every supervisor session start."
      />
      <PatternExplorerBody data={data} />
      <p className="mt-4 text-[10px] text-(--qs-text-3)">Reference: {data.docs_path}</p>
    </V4Card>
  );
}
