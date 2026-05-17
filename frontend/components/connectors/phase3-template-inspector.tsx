"use client";

import { ExternalLink, Loader2Icon, X } from "lucide-react";

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
      ? "fixed inset-x-0 bottom-0 z-[60] max-h-[min(88vh,920px)] rounded-t-[28px] border border-[#1e2348] bg-[#070716]/98 pb-[env(safe-area-inset-bottom)] shadow-[0_-40px_120px_rgb(0_0_0/0.55)] backdrop-blur-md xl:hidden"
      : "sticky top-24 hidden h-fit max-h-[calc(100vh-8rem)] overflow-y-auto rounded-[26px] border border-[#252a55] bg-black/80 p-5 shadow-[inset_0_0_0_1px_rgb(255_184_0/0.08)] xl:block";

  return (
    <aside className={shell} role="dialog" aria-modal={layout === "sheet"} aria-labelledby={`phase3-${tpl.template_id}-title`}>
      <div className="flex items-start justify-between gap-3 border-b border-[#1e2348] pb-4">
        <div className="min-w-0 space-y-1">
          <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-cyan">{tpl.template_id}</p>
          <h2 id={`phase3-${tpl.template_id}-title`} className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-pollen">
            {tpl.title}
          </h2>
          <p className="font-[family-name:var(--font-poppins)] text-xs leading-relaxed text-zinc-400">{tpl.summary}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-white/12 text-zinc-300 hover:bg-white/5 touch-manipulation"
          aria-label="Close inspector"
        >
          <X className="h-5 w-5" aria-hidden />
        </button>
      </div>

      <dl className="mt-4 grid gap-3 font-[family-name:var(--font-poppins)] text-xs text-zinc-400 md:grid-cols-2">
        <div>
          <dt className="uppercase tracking-[0.28em] text-zinc-500">Slug</dt>
          <dd className="font-mono text-[13px] text-[#B7F6FF]">{tpl.suggested_slug}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-[0.28em] text-zinc-500">Auth</dt>
          <dd className="text-[#D7D9FF]">{tpl.auth_type}</dd>
        </div>
        <div className="md:col-span-2">
          <dt className="uppercase tracking-[0.28em] text-zinc-500">Managers</dt>
          <dd className="text-[#D7D9FF]">{tpl.suggested_manager_slugs.length ? tpl.suggested_manager_slugs.join(", ") : "All lanes"}</dd>
        </div>
        <div className="md:col-span-2">
          <dt className="uppercase tracking-[0.28em] text-zinc-500">Hub status</dt>
          <dd className={cn(hubRow?.is_active ? "text-[#00FF88]" : "text-magenta")}>
            {hubRow
              ? `${hubRow.is_active ? "Active" : "Inactive"} · ${hubRow.is_builtin ? "built-in" : "custom"} · last test ${tested ?? "never"}`
              : "Not provisioned — instantiate or use forge."}
          </dd>
        </div>
      </dl>

      <div className="mt-4 space-y-2">
        <p className="font-[family-name:var(--font-poppins)] text-[11px] font-semibold uppercase tracking-[0.24em] text-zinc-500">MCP tools</p>
        <ul className="max-h-48 space-y-2 overflow-y-auto rounded-2xl border border-[#1a2045] bg-black/72 p-3 hive-scrollbar">
          {tpl.tools.map((tool) => (
            <li key={tool.name} className="border-b border-white/[0.04] pb-2 last:border-b-0 last:pb-0">
              <p className="font-mono text-[11px] text-pollen">
                {tool.method} {tool.name}
              </p>
              <p className="font-[family-name:var(--font-poppins)] text-[11px] text-zinc-500">{tool.description ?? tool.path}</p>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        <a
          href={tpl.documentation_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-2xl border border-cyan/35 px-4 py-3 font-[family-name:var(--font-poppins)] text-xs font-semibold text-cyan hover:bg-cyan/10 touch-manipulation"
        >
          Vendor docs
          <ExternalLink className="h-3.5 w-3.5" aria-hidden />
        </a>
        <button
          type="button"
          className="inline-flex min-h-[44px] flex-1 items-center justify-center rounded-2xl border border-pollen/40 px-4 py-3 font-[family-name:var(--font-poppins)] text-xs font-semibold text-pollen hover:bg-pollen/10 touch-manipulation"
          onClick={() => onPrefill(tpl)}
        >
          Prefill forge
        </button>
        <button
          type="button"
          disabled={provisioning}
          className="inline-flex min-h-[44px] flex-1 items-center justify-center rounded-2xl border border-[#00FF88]/35 px-4 py-3 font-[family-name:var(--font-poppins)] text-xs font-semibold text-[#00FF88] hover:bg-[#00FF88]/10 disabled:opacity-40 touch-manipulation"
          onClick={() => void onProvision(tpl)}
        >
          {provisioning ? <Loader2Icon className="mr-2 h-4 w-4 animate-spin" aria-hidden /> : null}
          Provision hub
        </button>
        {hubRow && onTestHub ? (
          <button
            type="button"
            disabled={busyTest}
            className="inline-flex min-h-[44px] flex-1 items-center justify-center rounded-2xl border border-white/15 px-4 py-3 font-[family-name:var(--font-poppins)] text-xs font-semibold text-zinc-100 hover:bg-white/5 disabled:opacity-40 touch-manipulation"
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
