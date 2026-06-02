"use client";

import { ChevronDown, ExternalLink, Loader2, Settings2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge } from "@/components/ui/v4";
import type { DynamicConnectorPayload } from "@/lib/connectors-types";
import type { Phase3CoverageRow, Phase3TemplatePublic } from "@/lib/connectors-phase3";
import { phase3CategoryLabel } from "@/lib/connectors-phase3";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";
import { cn } from "@/lib/utils";

export interface Phase3TemplateConfig {
  slug: string;
  displayName: string;
  baseUrl: string;
}

function defaultConfig(tpl: Phase3TemplatePublic): Phase3TemplateConfig {
  return {
    slug: tpl.suggested_slug,
    displayName: tpl.title,
    baseUrl: tpl.base_url ?? "",
  };
}

function findConnectorRow(
  rows: DynamicConnectorPayload[],
  slug: string,
): DynamicConnectorPayload | undefined {
  const needle = slug.trim().toLowerCase();
  return rows.find((row) => row.slug.trim().toLowerCase() === needle);
}

interface Phase3TemplateCardProps {
  readonly tpl: Phase3TemplatePublic;
  readonly provisioned: boolean;
  readonly connectorRows: DynamicConnectorPayload[];
  readonly instantiatingId: string | null;
  readonly onPrefill: (tpl: Phase3TemplatePublic, config: Phase3TemplateConfig) => void;
  readonly onProvision: (tpl: Phase3TemplatePublic, config: Phase3TemplateConfig) => void;
}

function Phase3TemplateCard({
  tpl,
  provisioned,
  connectorRows,
  instantiatingId,
  onPrefill,
  onProvision,
}: Phase3TemplateCardProps): JSX.Element {
  const [configOpen, setConfigOpen] = useState(false);
  const [config, setConfig] = useState<Phase3TemplateConfig>(() => defaultConfig(tpl));
  const busy = instantiatingId === tpl.template_id;
  const effectiveSlug = config.slug.trim() || tpl.suggested_slug;
  const rowForSlug = findConnectorRow(connectorRows, effectiveSlug);
  const isProvisioned = provisioned || Boolean(rowForSlug);
  const isActive = Boolean(rowForSlug?.is_active);

  useEffect(() => {
    setConfig(defaultConfig(tpl));
    setConfigOpen(false);
  }, [tpl]);

  const toggleConfigure = (): void => {
    setConfigOpen((open) => {
      const next = !open;
      if (next) {
        onPrefill(tpl, config);
      }
      return next;
    });
  };

  return (
    <article className={cn("hub-catalog-card phase3-template-card", configOpen && "phase3-template-card--open")}>
      <header className="phase3-template-card__head">
        <p className="phase3-template-card__title">{tpl.title}</p>
        <p className="phase3-template-card__summary">{tpl.summary}</p>
      </header>

      <div className="phase3-template-card__manifest">
        <p className="phase3-template-card__manifest-label">MCP manifest</p>
        <p className="phase3-template-card__manifest-meta">
          Auth <span className="font-mono text-(--qs-text)">{tpl.auth_type}</span>
          <span aria-hidden> · </span>
          {tpl.tool_count} tool{tpl.tool_count === 1 ? "" : "s"}
        </p>
        <div className="phase3-template-card__status-row">
          <p className={isProvisioned ? "phase3-template-card__status phase3-template-card__status--ok" : "phase3-template-card__status phase3-template-card__status--pending"}>
            {isProvisioned ? "In roster" : "Not provisioned"}
          </p>
          {isProvisioned ? (
            <V4Badge tone={isActive ? "ok" : "warn"}>{isActive ? "Active" : "Needs credentials"}</V4Badge>
          ) : null}
        </div>
      </div>

      {configOpen ? (
        <div className="phase3-template-card__config">
          <p className="phase3-template-card__config-title">
            <Settings2 className="size-3.5" aria-hidden />
            Configure before provision
          </p>
          <label className="phase3-template-field">
            <span className="phase3-template-field__label">Slug</span>
            <input
              type="text"
              className="qs-input font-mono text-xs"
              value={config.slug}
              onChange={(event) => setConfig((prev) => ({ ...prev, slug: event.target.value }))}
              placeholder={tpl.suggested_slug}
            />
          </label>
          <label className="phase3-template-field">
            <span className="phase3-template-field__label">Display name</span>
            <input
              type="text"
              className="qs-input text-xs"
              value={config.displayName}
              onChange={(event) => setConfig((prev) => ({ ...prev, displayName: event.target.value }))}
              placeholder={tpl.title}
            />
          </label>
          <label className="phase3-template-field">
            <span className="phase3-template-field__label">Base URL</span>
            <input
              type="url"
              className="qs-input font-mono text-xs"
              value={config.baseUrl}
              onChange={(event) => setConfig((prev) => ({ ...prev, baseUrl: event.target.value }))}
              placeholder="https://api.example.com"
            />
          </label>
          {isProvisioned && rowForSlug ? (
            <Link
              href={`/integrations?tab=hub&hubSection=vault#hub-vault`}
              className="text-[11px] text-cyan hover:underline"
            >
              Seal secrets in Connector Vault →
            </Link>
          ) : null}
        </div>
      ) : null}

      <footer className="phase3-template-card__foot">
        {configOpen ? (
          <code className="phase3-template-card__slug">{config.slug.trim() || tpl.suggested_slug}</code>
        ) : (
          <span className="phase3-template-card__slug phase3-template-card__slug--ghost" aria-hidden />
        )}
        <div className="phase3-template-card__actions">
          <a
            href={tpl.documentation_url}
            target="_blank"
            rel="noreferrer"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
          >
            Docs
            <ExternalLink className="size-3" aria-hidden />
          </a>
          <button
            type="button"
            className={cn("qs-btn qs-btn--ghost qs-btn--sm gap-1", configOpen && "border-pollen/40 text-pollen")}
            onClick={toggleConfigure}
          >
            Pre-fill
            <ChevronDown className={cn("size-3.5 transition", configOpen && "rotate-180")} aria-hidden />
          </button>
          <button
            type="button"
            disabled={busy || !config.slug.trim()}
            className="qs-btn qs-btn--primary qs-btn--sm min-w-[5.5rem]"
            onClick={() => onProvision(tpl, config)}
          >
            {busy ? <Loader2 className="size-3.5 animate-spin" aria-hidden /> : "Provision"}
          </button>
        </div>
      </footer>
    </article>
  );
}

interface Phase3TemplatesGridProps {
  readonly category: string;
  readonly templates: Phase3TemplatePublic[];
  readonly coverage: Phase3CoverageRow[];
  readonly connectorRows: DynamicConnectorPayload[];
  readonly instantiatingId: string | null;
  readonly onPrefill: (tpl: Phase3TemplatePublic, config: Phase3TemplateConfig) => void;
  readonly onProvision: (tpl: Phase3TemplatePublic, config: Phase3TemplateConfig) => void;
  readonly showSectionHead?: boolean;
}

/** Full-width Phase 3 template cards — 2×2 grid with bottom pagination. */
export function Phase3TemplatesGrid({
  category,
  templates,
  coverage,
  connectorRows,
  instantiatingId,
  onPrefill,
  onProvision,
  showSectionHead = true,
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
    <div className="phase3-templates-grid-wrap min-w-0 space-y-3">
      {showSectionHead ? (
        <div className="phase3-templates-grid-head flex flex-wrap items-center gap-2">
          <p className="phase3-templates-grid-head__label">{phase3CategoryLabel(category).toUpperCase()}</p>
          <V4Badge tone="info">{templates.length} templates</V4Badge>
        </div>
      ) : null}

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
        <div className="hub-catalog-grid phase3-templates-grid">
          {pagination.slice.map((tpl) => (
              <Phase3TemplateCard
                key={tpl.template_id}
                tpl={tpl}
                provisioned={provisionedById.get(tpl.template_id) ?? false}
                connectorRows={connectorRows}
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
