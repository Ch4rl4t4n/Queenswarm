"use client";

import type { JSX } from "react";

import { Loader2Icon } from "lucide-react";
import useSWR from "swr";

import { V4Badge } from "@/components/ui/v4";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { HiveApiError, hiveGet } from "@/lib/api";
import type { SupervisorSharedContextRow } from "@/lib/hive-types";
interface AgentSessionSharedContextPanelProps {
  sessionId: string;
}

function sectionPreview(value: unknown): string {
  if (value === null || value === undefined) {
    return "empty";
  }
  if (Array.isArray(value)) {
    return `${value.length} rows`;
  }
  if (typeof value === "object") {
    return `${Object.keys(value as Record<string, unknown>).length} fields`;
  }
  return String(value).slice(0, 120);
}

export function AgentSessionSharedContextPanel({ sessionId }: AgentSessionSharedContextPanelProps): JSX.Element {
  const { data, error, isLoading, mutate } = useSWR<SupervisorSharedContextRow>(
    sessionId ? `agents/sessions/${sessionId}/shared-context` : null,
    () => hiveGet<SupervisorSharedContextRow>(`agents/sessions/${sessionId}/shared-context`),
    { revalidateOnFocus: false },
  );

  const contract =
    data?.retrieval_contract ||
    (typeof data?.context_summary?.retrieval_contract === "string"
      ? data.context_summary.retrieval_contract
      : "");

  return (
    <div className="rounded-xl border border-cyan/20 bg-black/30 p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-cyan">Shared memory</p>
          <p className="mt-1 text-[11px] text-zinc-500">Hive Mind + graph retrieval via contract</p>
        </div>
        <HiveRefreshButton busy={isLoading} className="qs-btn--xs" onClick={() => void mutate()} />
      </div>

      {isLoading ? (
        <div className="mt-3 flex items-center gap-2 text-xs text-zinc-500">
          <Loader2Icon className="h-4 w-4 animate-spin text-pollen" aria-hidden />
          Resolving retrieval bundle…
        </div>
      ) : error ? (
        <p className="mt-3 text-xs text-danger">
          {error instanceof HiveApiError ? error.message : "Shared context unavailable."}
        </p>
      ) : !data || Array.isArray(data) ? (
        <p className="mt-3 text-xs text-zinc-500">No shared context payload.</p>
      ) : (
        <div className="mt-3 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <V4Badge tone={data.enabled ? "ok" : "warn"}>
              {data.enabled ? "retrieval on" : "retrieval disabled"}
            </V4Badge>
            {contract ? (
              <span className="font-mono text-[10px] text-zinc-400">{contract}</span>
            ) : (
              <span className="text-[10px] text-zinc-600">no contract</span>
            )}
          </div>

          {(data.matched_sections ?? []).length > 0 ? (
            <ul className="space-y-1">
              {data.matched_sections.map((section) => (
                <li
                  key={section}
                  className="flex items-center justify-between gap-2 rounded-lg bg-black/25 px-2 py-1.5 text-[11px]"
                >
                  <span className="font-mono text-pollen">{section}</span>
                  <span className="text-zinc-500">
                    {sectionPreview(data.sections[section])}
                    {data.relevance_scores?.[section] !== undefined
                      ? ` · ${data.relevance_scores[section].toFixed(2)}`
                      : ""}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[11px] text-zinc-500">No matched sections — set a retrieval contract when spawning.</p>
          )}

          {data.pruned_items > 0 ? (
            <p className="text-[10px] text-zinc-600">Auto-pruned low-relevance items: {data.pruned_items}</p>
          ) : null}

          {data.prompt_block ? (
            <pre className="max-h-32 overflow-auto rounded-lg bg-black/40 p-2 font-mono text-[10px] text-zinc-300">
              {data.prompt_block}
            </pre>
          ) : null}
        </div>
      )}
    </div>
  );
}
