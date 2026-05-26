"use client";

import { BookOpen, ExternalLink, Loader2, Rocket } from "lucide-react";
import { useMemo } from "react";

import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge } from "@/components/ui/v4";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";

type ConnectionStatus = "active" | "ready_to_test" | "needs_credentials" | "inactive";

export interface ExecutionStackConnection {
  readonly id: string;
  readonly slug: string;
  readonly display_name: string;
  readonly auth_type: string;
  readonly status: ConnectionStatus;
  readonly is_active: boolean;
  readonly tools_count: number;
  readonly agent_usage?: string | null;
  readonly doc_url?: string | null;
}

function statusTone(status: ConnectionStatus): "ok" | "warn" | "err" | "info" {
  if (status === "active") return "ok";
  if (status === "ready_to_test") return "info";
  if (status === "needs_credentials") return "warn";
  return "err";
}

function statusLabel(status: ConnectionStatus): string {
  if (status === "active") return "ready";
  if (status === "ready_to_test") return "test to activate";
  if (status === "needs_credentials") return "needs credentials";
  return "not connected";
}

function authCategory(authType: string): string {
  return authType.replaceAll("_", " ").toUpperCase();
}

function defaultAgentUsage(connection: ExecutionStackConnection): string {
  return `Supervisor lanes invoke ${connection.tools_count} tool${connection.tools_count === 1 ? "" : "s"} from ${connection.slug} during verified execution flows.`;
}

interface ExecutionStackCardProps {
  readonly connection: ExecutionStackConnection;
  readonly testBusy: boolean;
  readonly onOpenGuide: (slug: string) => void;
  readonly onTest: (connection: ExecutionStackConnection) => void;
  readonly onDryRun: (connection: ExecutionStackConnection) => void;
}

function ExecutionStackCard({
  connection,
  testBusy,
  onOpenGuide,
  onTest,
  onDryRun,
}: ExecutionStackCardProps): JSX.Element {
  const agentUsage = connection.agent_usage?.trim() || defaultAgentUsage(connection);

  return (
    <article className="v4-dream-cycle-card flex h-full flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-semibold text-(--qs-text)">{connection.display_name}</p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">
            {authCategory(connection.auth_type)}
          </p>
        </div>
        <V4Badge tone={statusTone(connection.status)}>{statusLabel(connection.status)}</V4Badge>
      </div>

      <p className="line-clamp-2 text-xs leading-relaxed text-(--qs-text-3)">{agentUsage}</p>

      <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-3 py-2">
        <p className="v4-field-label text-[10px] text-cyan-300/90">How agents use this</p>
        <p className="mt-1 text-xs leading-relaxed text-(--qs-text-2)">{agentUsage}</p>
      </div>

      <p className="font-mono text-[11px] text-(--qs-text-3)">
        {connection.slug} · {connection.auth_type} · {connection.tools_count} tools
      </p>

      <div className="flex flex-wrap gap-2">
        <V4Badge tone={connection.is_active ? "ok" : "warn"}>
          {connection.is_active ? "active" : "paused"}
        </V4Badge>
        <V4Badge tone="info">{connection.tools_count} tools</V4Badge>
        {connection.status === "needs_credentials" ? <V4Badge tone="warn">credentials</V4Badge> : null}
        {connection.status === "ready_to_test" ? <V4Badge tone="info">test pending</V4Badge> : null}
      </div>

      {connection.doc_url ? (
        <a
          href={connection.doc_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs text-pollen hover:underline"
        >
          <ExternalLink className="h-3.5 w-3.5" aria-hidden />
          Provider docs &amp; pricing
        </a>
      ) : null}

      <div className="mt-auto flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="qs-btn qs-btn--primary qs-btn--sm gap-1.5"
          onClick={() => onOpenGuide(connection.slug)}
        >
          <BookOpen className="h-3.5 w-3.5" aria-hidden />
          Setup guide
        </button>
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm"
          disabled={testBusy}
          onClick={() => onTest(connection)}
        >
          {testBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
          Test
        </button>
        {connection.status === "active" ? (
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-1" onClick={() => onDryRun(connection)}>
            <Rocket className="h-3.5 w-3.5" aria-hidden />
            Dry-run tool
          </button>
        ) : null}
      </div>
    </article>
  );
}

interface ExecutionStackGridProps {
  readonly connections: ExecutionStackConnection[];
  readonly loading: boolean;
  readonly testBusyId: string | null;
  readonly onOpenGuide: (slug: string) => void;
  readonly onTest: (connection: ExecutionStackConnection) => void;
  readonly onDryRun: (connection: ExecutionStackConnection) => void;
}

/** Marketplace-style 2×2 execution stack — paginated, no inner scroll. */
export function ExecutionStackGrid({
  connections,
  loading,
  testBusyId,
  onOpenGuide,
  onTest,
  onDryRun,
}: ExecutionStackGridProps): JSX.Element {
  const pageSize = useGridTwoRowPageSize({ columns: 2 });
  const resetKey = useMemo(
    () => connections.map((row) => `${row.id}:${row.status}:${row.tools_count}`).join("|"),
    [connections],
  );
  const pagination = usePaginatedSlice(connections, pageSize, `${resetKey}|${pageSize}|${connections.length}`);

  if (loading) {
    return (
      <div className="grid gap-3 md:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="v4-dream-cycle-card h-[240px] animate-pulse bg-white/5" />
        ))}
      </div>
    );
  }

  if (connections.length === 0) {
    return (
      <div className="qs-bubble-inner border-dashed px-4 py-8 text-center">
        <p className="text-sm text-(--qs-text-2)">No execution connections yet.</p>
        <p className="mt-1 text-xs text-(--qs-text-3)">
          Install a template from Marketplace, connect credentials, then test to activate.
        </p>
      </div>
    );
  }

  return (
    <ViewportBoundedPanel
      className="v4-recipe-catalog-panel"
      footer={
        <ListPaginator
          page={pagination.page}
          totalPages={pagination.totalPages}
          totalItems={pagination.totalItems}
          pageSize={pageSize}
          onPageChange={pagination.setPage}
        />
      }
    >
      <div className="grid gap-3 md:grid-cols-2">
        {pagination.slice.map((connection) => (
          <ExecutionStackCard
            key={connection.id}
            connection={connection}
            testBusy={testBusyId === connection.id}
            onOpenGuide={onOpenGuide}
            onTest={onTest}
            onDryRun={onDryRun}
          />
        ))}
      </div>
    </ViewportBoundedPanel>
  );
}
