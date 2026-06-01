"use client";

import { useEffect, useMemo, useState } from "react";

import { HubCategoryCatalogShell } from "@/components/connectors/hub-category-catalog-shell";
import { Phase3TemplatesGrid, type Phase3TemplateConfig } from "@/components/connectors/phase3-templates-grid";
import type { DynamicConnectorPayload } from "@/lib/connectors-types";
import {
  orderedPhase3Categories,
  phase3CategoryLabel,
  phase3CategoryShortLabel,
  phase3ProvisionCoverage,
  type Phase3CatalogSlice,
  type Phase3TemplatePublic,
} from "@/lib/connectors-phase3";

export interface Phase3TemplatesPanelProps {
  phase3Slice: Phase3CatalogSlice;
  connectorRows: DynamicConnectorPayload[];
  instantiatingId: string | null;
  overviewBusy: boolean;
  overviewErr: string | null;
  pulse: { provisioned: number; active: number; total: number };
  onRefresh: () => void | Promise<void>;
  onPrefill: (tpl: Phase3TemplatePublic, config: Phase3TemplateConfig) => void;
  onProvision: (tpl: Phase3TemplatePublic, config: Phase3TemplateConfig) => void | Promise<void>;
  /** When true, skip outer V4Card (Integrations hub already wraps siblings). */
  embedded?: boolean;
}

/** Phase 3 MCP template catalog — category bubbles + configurable provision grid. */
export function Phase3TemplatesPanel({
  phase3Slice,
  connectorRows,
  instantiatingId,
  overviewBusy,
  overviewErr,
  pulse,
  onRefresh,
  onPrefill,
  onProvision,
  embedded = true,
}: Phase3TemplatesPanelProps): JSX.Element {
  const categories = useMemo(() => orderedPhase3Categories(phase3Slice.grouped), [phase3Slice.grouped]);
  const [openCategory, setOpenCategory] = useState<string | null>(categories[0] ?? null);

  useEffect(() => {
    if (openCategory && categories.includes(openCategory)) {
      return;
    }
    setOpenCategory(categories[0] ?? null);
  }, [categories, openCategory]);

  const coverage = useMemo(
    () => phase3ProvisionCoverage(phase3Slice.templates, connectorRows.map((row) => row.slug)),
    [connectorRows, phase3Slice.templates],
  );

  const templates = openCategory ? (phase3Slice.grouped[openCategory] ?? []) : [];

  const catalogCategories = useMemo(
    () =>
      categories
        .map((category) => {
          const tpls = phase3Slice.grouped[category] ?? [];
          if (!tpls.length) {
            return null;
          }
          const provisionedInCat = tpls.filter((tpl) =>
            coverage.find((row) => row.template_id === tpl.template_id)?.provisioned,
          ).length;
          return {
            id: category,
            label: phase3CategoryShortLabel(category),
            count: tpls.length,
            showDot: provisionedInCat > 0,
          };
        })
        .filter((row): row is NonNullable<typeof row> => row !== null),
    [categories, coverage, phase3Slice.grouped],
  );

  return (
    <HubCategoryCatalogShell
      embedded={embedded}
      className="phase3-templates-card"
      title="Phase 3 templates"
      description="MCP manifests — OAuth connect above, or pick a category bubble and provision."
      stats={[
        { label: `${pulse.provisioned}/${pulse.total} rostered`, tone: "info" },
        { label: `${pulse.active} active`, tone: "ok" },
      ]}
      error={overviewErr}
      refreshBusy={overviewBusy}
      onRefresh={onRefresh}
      categories={catalogCategories}
      openCategory={openCategory}
      onCategoryChange={setOpenCategory}
      sectionLabel={openCategory ? phase3CategoryLabel(openCategory) : "Templates"}
      sectionCount={templates.length}
      sectionItemLabel="templates"
    >
      {templates.length > 0 ? (
        <Phase3TemplatesGrid
          category={openCategory ?? ""}
          templates={templates}
          coverage={coverage}
          connectorRows={connectorRows}
          instantiatingId={instantiatingId}
          onPrefill={onPrefill}
          onProvision={onProvision}
          showSectionHead={false}
        />
      ) : null}
    </HubCategoryCatalogShell>
  );
}
