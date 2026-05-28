"use client";

import { useMemo } from "react";

import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge } from "@/components/ui/v4";
import type { Phase3CoverageRow, Phase3TemplatePublic } from "@/lib/connectors-phase3";
import { phase3CategoryLabel } from "@/lib/connectors-phase3";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";

interface Phase3TemplateCardProps {
  readonly tpl: Phase3TemplatePublic;
  readonly provisioned: boolean;
  readonly instantiatingId: string | null;
  readonly onPrefill: (tpl: Phase3TemplatePublic) => void;
  readonly onProvision: (tpl: Phase3TemplatePublic) => void;
}

function Phase3TemplateCard({
  tpl,
  provisioned,
  instantiatingId,
  onPrefill,
  onProvision,
}: Phase3TemplateCardProps): JSX.Element {
  const busy = instantiatingId === tpl.template_id;

  return (
    <article className="v4-dream-cycle-card flex h-full flex-col gap-3">
      <header className="space-y-1">
        <p className="text-sm font-semibold leading-tight text-(--qs-text)">{tpl.title}</p>
        <p className="line-clamp-2 text-xs leading-relaxed text-(--qs-text-3)">{tpl.summary}</p>
      </header>

      <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-3 py-2">
        <p className="v4-field-label text-[10px] text-cyan-300/90">MCP manifest</p>
        <p className="mt-1 text-xs leading-relaxed text-(--qs-text-2)">
          Auth <span className="font-mono text-(--qs-text)">{tpl.auth_type}</span> ·{" "}
          {tpl.tool_count} tool{tpl.tool_count === 1 ? "" : "s"}
        </p>
        <p className={provisioned ? "mt-2 text-xs text-(--qs-green)" : "mt-2 text-xs text-(--qs-magenta)"}>
          {provisioned ? "In roster" : "Not provisioned"}
        </p>
      </div>

      <p className="font-mono text-[11px] text-(--qs-text-3)">{tpl.suggested_slug}</p>

      <div className="v4-dream-cycle-card-actions">
        <a
          href={tpl.documentation_url}
          target="_blank"
          rel="noreferrer"
          className="qs-btn qs-btn--ghost qs-btn--sm"
        >
          Docs
        </a>
        <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => onPrefill(tpl)}>
          Prefill
        </button>
        <button
          type="button"
          disabled={busy}
          className="qs-btn qs-btn--primary qs-btn--sm"
          onClick={() => onProvision(tpl)}
        >
          {busy ? "…" : "Provision"}
        </button>
      </div>
    </article>
  );
}

interface Phase3TemplatesGridProps {
  readonly category: string;
  readonly templates: Phase3TemplatePublic[];
  readonly coverage: Phase3CoverageRow[];
  readonly instantiatingId: string | null;
  readonly onPrefill: (tpl: Phase3TemplatePublic) => void;
  readonly onProvision: (tpl: Phase3TemplatePublic) => void;
}

/** Full-width Phase 3 template cards — 2×2 grid with bottom pagination (Colonies pattern). */
export function Phase3TemplatesGrid({
  category,
  templates,
  coverage,
  instantiatingId,
  onPrefill,
  onProvision,
}: Phase3TemplatesGridProps): JSX.Element {
  const pageSize = useGridTwoRowPageSize({ columns: 2 });
  const resetKey = useMemo(() => templates.map((tpl) => tpl.template_id).join("|"), [templates]);
  const pagination = usePaginatedSlice(templates, pageSize, `${category}|${resetKey}|${pageSize}|${templates.length}`);

  const provisionedById = useMemo(() => {
    const map = new Map<string, boolean>();
    for (const row of coverage) {
      map.set(row.template_id, row.provisioned);
    }
    return map;
  }, [coverage]);

  return (
    <div className="min-w-0 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">
          {phase3CategoryLabel(category)}
        </p>
        <V4Badge tone="info">{templates.length} templates</V4Badge>
      </div>

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
        <div className="phase3-templates-grid">
          {pagination.slice.map((tpl) => (
            <Phase3TemplateCard
              key={tpl.template_id}
              tpl={tpl}
              provisioned={provisionedById.get(tpl.template_id) ?? false}
              instantiatingId={instantiatingId}
              onPrefill={onPrefill}
              onProvision={onProvision}
            />
          ))}
        </div>
      </ViewportBoundedPanel>
    </div>
  );
}
