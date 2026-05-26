"use client";

import { memo, useCallback, useEffect, useState } from "react";

import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";

interface ManualSection {
  id: string;
  title: string;
  audience?: string;
  order?: number;
  summary?: string;
  content_md: string;
  steps?: Array<{ step: number; action: string; detail: string }>;
}

interface StudioManual {
  version: string;
  title: string;
  summary: string;
  sections: ManualSection[];
  flows?: Array<{ id: string; label: string; section_ids: string[] }>;
  agent_quick_reference?: string;
}

let manualCache: StudioManual | null = null;

export interface ExecutionStudioManualPanelProps {
  onError: (message: string | null) => void;
}

function ExecutionStudioManualPanelInner({ onError }: ExecutionStudioManualPanelProps) {
  const [manual, setManual] = useState<StudioManual | null>(manualCache);
  const [loading, setLoading] = useState(!manualCache);

  const loadManual = useCallback(async () => {
    if (manualCache) {
      setManual(manualCache);
      setLoading(false);
      return;
    }
    setLoading(true);
    onError(null);
    try {
      const data = await hiveGet<StudioManual>("execution-studio/manual");
      manualCache = data;
      setManual(data);
    } catch (exc) {
      onError(exc instanceof HiveApiError ? exc.message : "Failed to load manual.");
    } finally {
      setLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    void loadManual();
  }, [loadManual]);

  return (
    <div className="space-y-4">
      {loading ? (
        <p className="text-sm text-(--qs-text-3)">Loading manual…</p>
      ) : manual ? (
        <>
          <div className="qs-bubble qs-bubble--tint-amber p-4">
            <p className="text-sm font-semibold text-(--qs-text)">{manual.title}</p>
            <p className="mt-1 text-xs text-(--qs-text-3)">{manual.summary}</p>
            <p className="mt-2 font-mono text-[10px] text-(--qs-text-4)">
              v{manual.version} · API /execution-studio/manual · skill: execution-studio
            </p>
          </div>
          {manual.flows?.map((flow) => (
            <div key={flow.id} className="qs-bubble-inner p-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-cyan">{flow.label}</p>
              <p className="mt-1 text-[10px] text-(--qs-text-4)">Sections: {flow.section_ids.join(" → ")}</p>
            </div>
          ))}
          {manual.sections.map((section) => (
            <article key={section.id} id={`manual-${section.id}`} className="qs-bubble p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p className="text-sm font-semibold text-(--qs-text)">{section.title}</p>
                {section.audience ? <V4Badge tone="info">{section.audience}</V4Badge> : null}
              </div>
              {section.summary ? <p className="mt-1 text-xs text-(--qs-text-3)">{section.summary}</p> : null}
              <div className="prose prose-invert mt-3 max-w-none whitespace-pre-wrap text-xs leading-relaxed text-(--qs-text-2)">
                {section.content_md}
              </div>
              {section.steps?.length ? (
                <ol className="mt-3 space-y-2 border-t border-(--qs-border)/40 pt-3">
                  {section.steps.map((step) => (
                    <li key={step.step} className="flex gap-2 text-xs text-(--qs-text-2)">
                      <span className="font-mono text-pollen">{step.step}.</span>
                      <span>
                        <span className="font-semibold text-(--qs-text)">{step.action}</span>
                        <span className="mt-0.5 block text-(--qs-text-3)">{step.detail}</span>
                      </span>
                    </li>
                  ))}
                </ol>
              ) : null}
            </article>
          ))}
          {manual.agent_quick_reference ? (
            <article className="qs-bubble qs-bubble--tint-green p-4">
              <p className="text-sm font-semibold text-(--qs-green)">Agent quick reference</p>
              <p className="mt-2 whitespace-pre-wrap text-xs text-(--qs-text-2)">{manual.agent_quick_reference}</p>
            </article>
          ) : null}
        </>
      ) : (
        <p className="text-sm text-(--qs-text-3)">Manual unavailable.</p>
      )}
    </div>
  );
}

export const ExecutionStudioManualPanel = memo(ExecutionStudioManualPanelInner);
