"use client";

import Link from "next/link";
import { BookMarked, Loader2, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

interface CitedRecallSource {
  source_id: string;
  source_type: "curated_memory" | "hive_mind" | "session" | "vault";
  label: string;
  snippet: string;
  similarity: number | null;
  href: string | null;
}

interface CitedRecallState {
  enabled: boolean;
  query: string;
  in_memory: boolean;
  status: "found" | "partial" | "not_in_memory";
  answer: string;
  citations: CitedRecallSource[];
  citation_count: number;
  operator_hint: string;
  filter_active?: boolean;
  active_filter_tag_ids?: string[];
  active_filter_labels?: string[];
}

function statusTone(status: CitedRecallState["status"]): string {
  if (status === "found") {
    return "border-success/35 bg-success/5";
  }
  if (status === "partial") {
    return "border-pollen/35 bg-pollen/5";
  }
  return "border-(--qs-border) bg-black/15";
}

/** MEM2 — Cited recall: answer + source file/session or explicit not-in-memory. */
export function CitedRecallPanel(): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const [query, setQuery] = useState("gumroad launch priorities");
  const [state, setState] = useState<CitedRecallState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTagIds, setActiveTagIds] = useState<string[]>([]);

  useEffect(() => {
    void hiveGet<{ active_filter_tag_ids?: string[] }>("memory/curated/project-tags")
      .then((payload) => setActiveTagIds(payload.active_filter_tag_ids ?? []))
      .catch(() => setActiveTagIds([]));
  }, []);

  const runSearch = useCallback(async (searchQuery: string) => {
    const trimmed = searchQuery.trim();
    if (trimmed.length < 3) {
      setState(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const tagQuery =
        activeTagIds.length > 0 ? `&tags=${encodeURIComponent(activeTagIds.join(","))}` : "";
      const data = await hiveGet<CitedRecallState>(
        `memory/curated/cited-recall?q=${encodeURIComponent(trimmed)}${tagQuery}`,
      );
      setState(data);
    } catch (e) {
      setState(null);
      setError(e instanceof HiveApiError ? e.message : "Cited recall unavailable");
    } finally {
      setLoading(false);
    }
  }, [activeTagIds]);

  useEffect(() => {
    void runSearch(query);
  }, [query, runSearch]);

  if (!hasFeature("selective_recall")) {
    return null;
  }

  return (
    <V4Card className="border-cyan/25" data-testid="cited-recall-panel">
      <V4CardHeader
        leadingIcon={BookMarked}
        leadingIconTone="cyan"
        title="Cited recall"
        description="GBrain-style answer with citations — Brain Pack, HiveMind vectors, sessions, vault."
        hint={sectionHintNode("knowledgeCitedRecall")}
      />

      <div className="flex flex-wrap gap-2">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-(--qs-text-4)" aria-hidden />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask what hive memory knows…"
            className="qs-input w-full pl-9"
            aria-label="Cited recall question"
          />
        </div>
        <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void runSearch(query)} disabled={loading}>
          Search memory
        </button>
      </div>

      {loading ? (
        <p className="mt-3 flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Searching hive memory…
        </p>
      ) : null}

      {error ? <p className="mt-3 text-sm text-(--qs-red)">{error}</p> : null}

      {state?.enabled ? (
        <div className={cn("mt-3 rounded-xl border p-3", statusTone(state.status))}>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <V4Badge tone="gold">MEM2</V4Badge>
            <V4Badge tone={state.status === "found" ? "ok" : state.status === "partial" ? "warn" : "info"}>
              {state.status.replace("_", " ")}
            </V4Badge>
            <V4Badge tone={state.in_memory ? "ok" : "err"}>
              {state.in_memory ? "in memory" : "not in memory"}
            </V4Badge>
            {state.filter_active ? (
              <V4Badge tone="warn">
                MEM5 · {(state.active_filter_labels ?? []).join(", ") || "slice"}
              </V4Badge>
            ) : null}
            <span className="font-mono text-[10px] text-(--qs-text-4)">{state.citation_count} cites</span>
          </div>

          <p className="text-sm leading-relaxed text-(--qs-text)">{state.answer}</p>
          <p className="mt-2 text-xs text-(--qs-text-3)">{state.operator_hint}</p>

          {state.citations.length > 0 ? (
            <ul className="mt-3 space-y-2">
              {state.citations.map((cite) => (
                <li key={cite.source_id} className="rounded-lg border border-(--qs-border)/70 bg-black/20 px-3 py-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-semibold text-(--qs-text)">{cite.label}</span>
                    <V4Badge tone="info">{cite.source_type.replace("_", " ")}</V4Badge>
                    {cite.similarity != null ? (
                      <span className="font-mono text-[10px] text-cyan">sim {Math.round(cite.similarity * 100)}%</span>
                    ) : null}
                  </div>
                  <p className="mt-1 text-xs text-(--qs-text-2)">{cite.snippet}</p>
                  {cite.href ? (
                    <Link href={cite.href} className="mt-1 text-[11px] text-cyan hover:underline">
                      Open source
                    </Link>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </V4Card>
  );
}
