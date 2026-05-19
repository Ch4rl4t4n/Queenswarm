"use client";

import { ExternalLink, Loader2Icon, X } from "lucide-react";

import { V4Badge } from "@/components/ui/v4";
import type { Phase3TemplatePublic } from "@/lib/connectors-phase3";
import type { DynamicConnectorPayload } from "@/lib/connectors-types";
import { cn } from "@/lib/utils";

export interface Phase3TemplateInspectorProps {
  tpl: Phase3TemplatePublic;
  hubRow: DynamicConnectorPayload | null;
  layout: "sheet" | "rail";
  onClose: () => void;
  onPrefill: (tpl: Phase3TemplatePublic) => void;
  onProvision: (tpl: Phase3TemplatePublic) => void;
  onTestHub?: (connectorId: string) => void;
  provisioning: boolean;
  testingId: string | null;
}

/** Responsive drill-in surface — bottom sheet on phones, sticky rail on desktop. */
export function Phase3TemplateInspector({
  tpl,
  hubRow,
  layout,
  onClose,
  onPrefill,
  onProvision,
  onTestHub,
  provisioning,
  testingId,
}: Phase3TemplateInspectorProps): JSX.Element {
  const tested = hubRow?.last_tested_at ?? null;
  const busyTest = hubRow ? testingId === hubRow.id : false;

  const shell =
    layout === "sheet"
      ? "fixed inset-x-0 bottom-0 z-[60] max-h-[min(88vh,920px)] rounded-t-(--qs-radius-lg) border border-(--qs-border) bg-(--qs-surface-2)/98 pb-[env(safe-area-inset-bottom)] shadow-[var(--qs-shadow-card)] backdrop-blur-md xl:hidden"
      : "v4-learning-panel sticky top-24 hidden h-fit max-h-[calc(100vh-8rem)] overflow-y-auto xl:block";

  return (
    <aside className={shell} role="dialog" aria-modal={layout === "sheet"} aria-labelledby={`phase3-${tpl.template_id}-title`}>
      <div className="flex items-start justify-between gap-3 border-b border-(--qs-border) pb-4">
        <div className="min-w-0 space-y-1">
          <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-(--qs-text-3)">{tpl.template_id}</p>
          <h2 id={`phase3-${tpl.template_id}-title`} className="text-lg font-semibold text-pollen">
            {tpl.title}
          </h2>
          <p className="text-xs leading-relaxed text-(--qs-text-3)">{tpl.summary}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="qs-btn qs-btn--ghost inline-flex h-11 w-11 shrink-0 items-center justify-center touch-manipulation"
          aria-label="Close inspector"
        >
          <X className="h-5 w-5" aria-hidden />
        </button>
      </div>

      <dl className="mt-4 grid gap-3 text-xs text-(--qs-text-2) md:grid-cols-2">
        <div>
          <dt className="v4-field-label">Slug</dt>
          <dd className="font-mono text-[13px] text-(--qs-text)">{tpl.suggested_slug}</dd>
        </div>
        <div>
          <dt className="v4-field-label">Auth</dt>
          <dd className="text-(--qs-text)">{tpl.auth_type}</dd>
        </div>
        <div className="md:col-span-2">
          <dt className="v4-field-label">Managers</dt>
          <dd className="text-(--qs-text)">{tpl.suggested_manager_slugs.length ? tpl.suggested_manager_slugs.join(", ") : "All lanes"}</dd>
        </div>
        <div className="md:col-span-2">
          <dt className="v4-field-label">Hub status</dt>
          <dd className={cn(hubRow?.is_active ? "text-(--qs-green)" : "text-(--qs-magenta)")}>
            {hubRow
              ? `${hubRow.is_active ? "Active" : "Inactive"} · ${hubRow.is_builtin ? "built-in" : "custom"} · last test ${tested ?? "never"}`
              : "Not provisioned — instantiate or use forge."}
          </dd>
        </div>
      </dl>

      <div className="mt-4 space-y-2">
        <p className="v4-field-label">MCP tools</p>
        <ul className="v4-event-log max-h-48 space-y-2 overflow-y-auto hive-scrollbar">
          {tpl.tools.map((tool) => (
            <li key={tool.name} className="border-b border-(--qs-border)/40 pb-2 last:border-b-0 last:pb-0">
              <p className="font-mono text-[11px] text-pollen">
                {tool.method} {tool.name}
              </p>
              <p className="text-[11px] text-(--qs-text-3)">{tool.description ?? tool.path}</p>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        <a
          href={tpl.documentation_url}
          target="_blank"
          rel="noreferrer"
          className="qs-btn qs-btn--ghost flex-1 gap-2 touch-manipulation"
        >
          Vendor docs
          <ExternalLink className="h-3.5 w-3.5" aria-hidden />
        </a>
        <button type="button" className="qs-btn qs-btn--ghost flex-1 touch-manipulation" onClick={() => onPrefill(tpl)}>
          Prefill forge
        </button>
        <button
          type="button"
          disabled={provisioning}
          className="qs-btn qs-btn--primary flex-1 touch-manipulation"
          onClick={() => void onProvision(tpl)}
        >
          {provisioning ? <Loader2Icon className="mr-2 h-4 w-4 animate-spin" aria-hidden /> : null}
          Provision hub
        </button>
        {hubRow && onTestHub ? (
          <button
            type="button"
            disabled={busyTest}
            className="qs-btn qs-btn--ghost flex-1 touch-manipulation"
            onClick={() => onTestHub(hubRow.id)}
          >
            {busyTest ? <Loader2Icon className="mr-2 h-4 w-4 animate-spin" aria-hidden /> : null}
            Test connection
          </button>
        ) : null}
      </div>
    </aside>
  );
}
