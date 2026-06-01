"use client";

import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { useMemo } from "react";

import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge } from "@/components/ui/v4";
import type { HarnessPatternRow, HarnessSkillRow } from "@/lib/hive-types";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";

interface McpToolEntry {
  key: string;
  slug: string;
  name: string;
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

function priorityTone(priority: number): "ok" | "info" | "warn" | "gold" {
  if (priority >= 90) {
    return "gold";
  }
  if (priority >= 75) {
    return "ok";
  }
  if (priority >= 50) {
    return "info";
  }
  return "warn";
}

function normalizeMcpTools(items: Record<string, unknown>[]): McpToolEntry[] {
  return items.map((tool, idx) => {
    const slug = String((tool as { connector_slug?: string }).connector_slug ?? "tool");
    const name = String((tool as { tool_name?: string }).tool_name ?? idx);
    return { key: `${slug}:${name}:${idx}`, slug, name };
  });
}

function McpToolMarketCard({ entry }: { entry: McpToolEntry }): JSX.Element {
  return (
    <article className="v4-dream-cycle-card flex h-full flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-semibold text-(--qs-text)">{entry.name}</p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">{entry.slug}</p>
        </div>
        <V4Badge tone="info">MCP</V4Badge>
      </div>

      <div className="rounded-xl bg-cyan-500/5 px-3 py-2">
        <p className="v4-field-label text-[10px] text-cyan-300/90">How agents use this</p>
        <p className="mt-1 text-xs leading-relaxed text-(--qs-text-2)">
          Supervisor lanes discover and invoke this tool via connector <span className="font-mono">{entry.slug}</span>.
        </p>
      </div>

      <p className="font-mono text-[11px] text-(--qs-text-3)">{entry.slug} · {entry.name}</p>
    </article>
  );
}

function SkillLatticeMarketCard({ skill }: { skill: HarnessSkillRow }): JSX.Element {
  return (
    <article className="v4-dream-cycle-card flex h-full flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <p className="line-clamp-2 text-sm font-semibold text-(--qs-text)">{skill.title}</p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">SkillLibrary</p>
        </div>
        <V4Badge tone={priorityTone(skill.priority)}>p{skill.priority}</V4Badge>
      </div>

      <div className="rounded-xl bg-pollen-500/5 px-3 py-2">
        <p className="v4-field-label text-[10px] text-pollen/90">Harness role</p>
        <p className="mt-1 text-xs leading-relaxed text-(--qs-text-2)">
          {skill.roles.length ? skill.roles.join(" · ") : "Active markdown skill shard for Queen harness routing."}
        </p>
      </div>

      <p className="font-mono text-[11px] text-(--qs-text-3)">{skill.slug}</p>

      <div className="v4-dream-cycle-card-actions">
        {skill.reference_mode ? <V4Badge tone="info">reference mode</V4Badge> : null}
        <V4Badge tone="purple">skill</V4Badge>
      </div>
    </article>
  );
}

function HarnessPatternMarketCard({ row }: { row: HarnessPatternRow }): JSX.Element {
  const sessionHref = `/agents?session=${encodeURIComponent(row.session_id)}`;
  const startedLabel = row.started_at
    ? new Date(row.started_at).toLocaleString("en-GB", {
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
          <p className="text-sm font-semibold text-(--qs-text)">Session {row.session_id.slice(0, 8)}</p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">{startedLabel}</p>
        </div>
        <V4Badge tone={sessionStatusTone(row.status)}>{row.status}</V4Badge>
      </div>

      <div className="rounded-xl bg-cyan-500/5 px-3 py-2">
        <p className="v4-field-label text-[10px] text-cyan-300/90">Pattern router selection</p>
        <p className="mt-1 text-xs leading-relaxed text-(--qs-text-2)">
          Primary: {row.primary.length ? row.primary.join(", ") : "—"}
        </p>
        {row.secondary.length ? (
          <p className="mt-1 text-xs text-(--qs-text-3)">Secondary: {row.secondary.join(", ")}</p>
        ) : null}
        {row.rationale[0] ? <p className="mt-2 text-xs text-(--qs-text-3)">Why: {row.rationale[0]}</p> : null}
      </div>

      <p className="font-mono text-[11px] text-(--qs-text-3)">{row.session_id.slice(0, 8)}…</p>

      <div className="flex flex-wrap gap-2">
        {row.primary.slice(0, 3).map((label) => (
          <V4Badge key={label} tone="gold">
            {label}
          </V4Badge>
        ))}
        {row.forced_reflection ? <V4Badge tone="info">reflection</V4Badge> : null}
      </div>

      <div className="v4-dream-cycle-card-actions">
        <Link
          href={sessionHref}
          className="inline-flex items-center gap-1 text-xs text-pollen hover:underline"
        >
          <ExternalLink className="h-3.5 w-3.5" aria-hidden />
          Supervisor lane
        </Link>
        <Link href={sessionHref} className="qs-btn qs-btn--ghost qs-btn--sm">
          Open session
        </Link>
      </div>
    </article>
  );
}

interface PaginatedGridProps<T> {
  items: T[];
  resetKey: string;
  renderItem: (item: T) => JSX.Element;
  emptyMessage: string;
}

function HarnessPaginatedMarketGrid<T>({ items, resetKey, renderItem, emptyMessage }: PaginatedGridProps<T>): JSX.Element {
  const pageSize = useGridTwoRowPageSize({ columns: 2 });
  const pagination = usePaginatedSlice(items, pageSize, `${resetKey}|${pageSize}|${items.length}`);

  if (items.length === 0) {
    return <p className="text-sm text-(--qs-muted)">{emptyMessage}</p>;
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
      <div className="grid gap-3 md:grid-cols-2">{pagination.slice.map((item) => renderItem(item))}</div>
    </ViewportBoundedPanel>
  );
}

/** MCP tools — marketplace grid inside harness collapsible. */
export function HarnessMcpToolGrid({ items }: { items: Record<string, unknown>[] }): JSX.Element {
  const normalized = useMemo(() => normalizeMcpTools(items), [items]);
  return (
    <HarnessPaginatedMarketGrid
      items={normalized}
      resetKey="harness-mcp"
      emptyMessage="No MCP tools provisioned — install a marketplace preset."
      renderItem={(entry) => <McpToolMarketCard key={entry.key} entry={entry} />}
    />
  );
}

/** Active skills — marketplace grid inside harness collapsible. */
export function HarnessSkillLatticeGrid({ skills }: { skills: HarnessSkillRow[] }): JSX.Element {
  return (
    <HarnessPaginatedMarketGrid
      items={skills}
      resetKey="harness-skills"
      emptyMessage="No active skills in SkillLibrary."
      renderItem={(skill) => <SkillLatticeMarketCard key={skill.slug} skill={skill} />}
    />
  );
}

/** Recent patterned sessions — marketplace grid inside harness collapsible. */
export function HarnessPatternGrid({ patterns }: { patterns: HarnessPatternRow[] }): JSX.Element {
  return (
    <HarnessPaginatedMarketGrid
      items={patterns}
      resetKey="harness-patterns"
      emptyMessage="No patterned sessions yet — run a supervisor task."
      renderItem={(row) => <HarnessPatternMarketCard key={row.session_id} row={row} />}
    />
  );
}
