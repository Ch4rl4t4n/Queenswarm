"use client";

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/utils";

export interface ChatFilter {
  id: string;
  label: string;
  text: string;
}

interface FiltersProps {
  readonly disabled?: boolean;
  /** Apply filter as Orchestrator session assignment (not chat input). */
  readonly onActivatePrompt: (filter: ChatFilter) => void;
  readonly onClearPrompt?: () => void;
  readonly activePromptId?: string | null;
  readonly activePromptLabel?: string | null;
  readonly storageKey?: string;
  readonly variant?: "default" | "v4";
}

const DEFAULT_FILTERS: ChatFilter[] = [
  {
    id: "brainstorm",
    label: "Brainstorm",
    text:
      "When the operator asks for ideas, respond with exactly 5 practical options. " +
      "For each option give one pro and one con, then recommend the best next action.",
  },
  {
    id: "code-review",
    label: "Code review",
    text:
      "When reviewing code or changes, focus on bugs, regressions, missing tests, and security risks. " +
      "Keep answers concise and prioritized by severity.",
  },
  {
    id: "daily-sync",
    label: "Daily sync",
    text:
      "When asked for status, respond with three sections: Done, Blocked, and Next 3 priorities for today. " +
      "Be brief and action-oriented.",
  },
];

const LABEL_MAX = 20;

function loadFilters(storageKey: string): ChatFilter[] {
  if (typeof window === "undefined") {
    return DEFAULT_FILTERS;
  }
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) {
      return DEFAULT_FILTERS;
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return DEFAULT_FILTERS;
    }
    const cleaned: ChatFilter[] = [];
    for (const item of parsed) {
      if (!item || typeof item !== "object") {
        continue;
      }
      const obj = item as Record<string, unknown>;
      const id = typeof obj.id === "string" ? obj.id : "";
      const label = typeof obj.label === "string" ? obj.label.slice(0, LABEL_MAX) : "";
      const text = typeof obj.text === "string" ? obj.text : "";
      if (id && label) {
        cleaned.push({ id, label, text });
      }
    }
    return cleaned.length > 0 ? cleaned : DEFAULT_FILTERS;
  } catch {
    return DEFAULT_FILTERS;
  }
}

function saveFilters(storageKey: string, filters: ChatFilter[]): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(storageKey, JSON.stringify(filters));
  } catch {
    // localStorage quota or disabled — fail silently
  }
}

function newFilterId(): string {
  return `flt-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function Filters({
  disabled = false,
  onActivatePrompt,
  onClearPrompt,
  activePromptId = null,
  activePromptLabel = null,
  storageKey = "qs-ballroom-filters",
  variant = "default",
}: FiltersProps) {
  const [filters, setFilters] = useState<ChatFilter[]>(DEFAULT_FILTERS);
  const [hydrated, setHydrated] = useState(false);
  const [editing, setEditing] = useState<ChatFilter | null>(null);
  const [draftLabel, setDraftLabel] = useState("");
  const [draftText, setDraftText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const labelInputRef = useRef<HTMLInputElement | null>(null);
  const labelId = useId();
  const textId = useId();

  useEffect(() => {
    setFilters(loadFilters(storageKey));
    setHydrated(true);
  }, [storageKey]);

  useEffect(() => {
    if (hydrated) {
      saveFilters(storageKey, filters);
    }
  }, [filters, hydrated, storageKey]);

  useEffect(() => {
    if (!editing) {
      return;
    }
    const t = window.setTimeout(() => labelInputRef.current?.focus(), 30);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setEditing(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.clearTimeout(t);
      window.removeEventListener("keydown", onKey);
    };
  }, [editing]);

  const openAdd = useCallback(() => {
    setEditing({ id: newFilterId(), label: "", text: "" });
    setDraftLabel("");
    setDraftText("");
    setError(null);
  }, []);

  const openEdit = useCallback((flt: ChatFilter) => {
    setEditing(flt);
    setDraftLabel(flt.label);
    setDraftText(flt.text);
    setError(null);
  }, []);

  const closeEdit = useCallback(() => {
    setEditing(null);
    setError(null);
  }, []);

  const handleSave = useCallback(() => {
    const label = draftLabel.trim().slice(0, LABEL_MAX);
    const text = draftText.trim();
    if (!label) {
      setError("Name is required.");
      return;
    }
    if (!text) {
      setError("Assignment brief is required.");
      return;
    }
    if (!editing) {
      return;
    }
    setFilters((prev) => {
      const existingIdx = prev.findIndex((f) => f.id === editing.id);
      if (existingIdx >= 0) {
        const next = [...prev];
        next[existingIdx] = { id: editing.id, label, text };
        return next;
      }
      return [...prev, { id: editing.id, label, text }];
    });
    setEditing(null);
    setError(null);
  }, [draftLabel, draftText, editing]);

  const removeFilter = useCallback((id: string) => {
    setFilters((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    if (filters.length === 0) {
      return;
    }
    if (!window.confirm(`Remove all ${filters.length} quick prompts?`)) {
      return;
    }
    setFilters([]);
  }, [filters.length]);

  const restoreDefaults = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  }, []);

  const labelLeft = useMemo(() => LABEL_MAX - draftLabel.length, [draftLabel]);
  const isV4 = variant === "v4";

  const isPromptActive = useCallback(
    (flt: ChatFilter) =>
      (activePromptId !== null && activePromptId === flt.id) ||
      (activePromptLabel !== null && activePromptLabel === flt.label),
    [activePromptId, activePromptLabel],
  );

  return (
    <div className="flex flex-col gap-2">
      {isV4 ? (
        <div className="v4-ballroom-filter-actions">
          <button
            type="button"
            disabled={disabled}
            className="qs-btn qs-btn--ghost qs-btn--sm"
            onClick={openAdd}
          >
            + Add
          </button>
          <button
            type="button"
            disabled={disabled}
            className="qs-btn qs-btn--ghost qs-btn--sm"
            onClick={restoreDefaults}
          >
            Restore defaults
          </button>
          <button
            type="button"
            disabled={disabled || filters.length === 0}
            className="qs-btn qs-btn--ghost qs-btn--sm"
            onClick={clearAll}
          >
            Clear all
          </button>
          {(activePromptId || activePromptLabel) && onClearPrompt ? (
            <button
              type="button"
              disabled={disabled}
              className="qs-btn qs-btn--ghost qs-btn--sm text-(--qs-amber)"
              onClick={onClearPrompt}
            >
              Clear assignment
            </button>
          ) : null}
        </div>
      ) : null}
      <div className={cn(isV4 ? "v4-chip-scroll items-center" : "flex flex-wrap items-center gap-1.5")}>
      {filters.map((flt) =>
        isV4 ? (
          <div
            key={flt.id}
            className={cn(
              "v4-filter-pill",
              disabled && "opacity-40",
              isPromptActive(flt) && "ring-1 ring-(--qs-amber)/70",
            )}
          >
            <span
              role="button"
              tabIndex={disabled ? -1 : 0}
              className={cn("cursor-pointer", disabled && "cursor-not-allowed")}
              onClick={() => !disabled && onActivatePrompt(flt)}
              onKeyDown={(e) => {
                if (!disabled && (e.key === "Enter" || e.key === " ")) {
                  e.preventDefault();
                  onActivatePrompt(flt);
                }
              }}
              title={flt.text}
            >
              {flt.label}
            </span>
            <button type="button" disabled={disabled} onClick={() => openEdit(flt)} title="Edit">
              ✎
            </button>
            <button type="button" disabled={disabled} onClick={() => removeFilter(flt.id)} title="Remove">
              ×
            </button>
          </div>
        ) : (
        <div
          key={flt.id}
          className={cn(
            "group inline-flex items-stretch overflow-hidden rounded border border-[var(--qs-border)] bg-[var(--qs-surface-2)] text-[10px] transition",
            disabled ? "opacity-40" : "hover:border-[var(--qs-cyan)]/45",
            isPromptActive(flt) && "border-[var(--qs-amber)]/70 ring-1 ring-[var(--qs-amber)]/40",
          )}
        >
          <button
            type="button"
            disabled={disabled}
            className="px-2 py-1 text-[var(--qs-text-3)] transition hover:text-[var(--qs-cyan)] disabled:cursor-not-allowed"
            onClick={() => onActivatePrompt(flt)}
            title={flt.text}
          >
            {flt.label}
          </button>
          <button
            type="button"
            disabled={disabled}
            className="border-l border-[var(--qs-border)] px-1.5 py-1 text-[10px] text-[var(--qs-text-3)] transition hover:text-[var(--qs-cyan)] disabled:cursor-not-allowed"
            onClick={() => openEdit(flt)}
            aria-label={`Edit quick prompt ${flt.label}`}
            title="Edit"
          >
            ✎
          </button>
          <button
            type="button"
            disabled={disabled}
            className="border-l border-[var(--qs-border)] px-1.5 py-1 text-[10px] text-[var(--qs-text-3)] transition hover:bg-[var(--qs-red)]/15 hover:text-[var(--qs-red)] disabled:cursor-not-allowed"
            onClick={() => removeFilter(flt.id)}
            aria-label={`Remove quick prompt ${flt.label}`}
            title="Remove"
          >
            ×
          </button>
        </div>
        )
      )}

      {!isV4 ? (
      <>
      <button
        type="button"
        disabled={disabled}
        className="inline-flex items-center gap-1 rounded border border-dashed border-[var(--qs-border)] px-2 py-1 text-[10px] text-[var(--qs-text-3)] transition hover:border-[var(--qs-cyan)]/45 hover:text-[var(--qs-cyan)] disabled:opacity-40"
        onClick={openAdd}
      >
        + Add prompt
      </button>

      {filters.length === 0 ? (
        <button
          type="button"
          disabled={disabled}
          className="inline-flex items-center gap-1 rounded border border-[var(--qs-border)] px-2 py-1 text-[10px] text-[var(--qs-text-3)] transition hover:border-[var(--qs-cyan)]/45 hover:text-[var(--qs-cyan)] disabled:opacity-40"
          onClick={restoreDefaults}
        >
          ↺ Restore defaults
        </button>
      ) : null}

      {(activePromptId || activePromptLabel) && onClearPrompt ? (
        <button
          type="button"
          disabled={disabled}
          className="inline-flex items-center gap-1 rounded border border-[var(--qs-amber)]/45 px-2 py-1 text-[10px] text-[var(--qs-amber)] transition hover:bg-[var(--qs-amber)]/10 disabled:opacity-40"
          onClick={onClearPrompt}
        >
          Clear assignment
        </button>
      ) : null}

      <div className="ml-auto flex items-center gap-1.5">
        <button
          type="button"
          disabled={disabled || filters.length === 0}
          className="rounded border border-[var(--qs-red)]/45 bg-[var(--qs-red)]/5 px-2 py-1 text-[10px] font-semibold text-[var(--qs-red)] transition hover:bg-[var(--qs-red)]/15 disabled:cursor-not-allowed disabled:opacity-40"
          onClick={clearAll}
        >
          Clear all prompts
        </button>
      </div>
      </>
      ) : null}
      </div>

      {editing ? (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 px-4 py-6 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label="Edit quick prompt"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              closeEdit();
            }
          }}
        >
          <div
            ref={dialogRef}
            className="qs-card flex w-full max-w-md flex-col gap-4 rounded-xl p-5 max-h-[min(90dvh,640px)] overflow-y-auto"
          >
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-[14px] font-semibold text-[var(--qs-text)]">
                {filters.some((f) => f.id === editing.id) ? "Edit quick prompt" : "Add quick prompt"}
              </h3>
              <button
                type="button"
                className="rounded border border-[var(--qs-border)] px-2 py-0.5 text-[11px] text-[var(--qs-text-3)] transition hover:text-[var(--qs-cyan)]"
                onClick={closeEdit}
                aria-label="Close"
              >
                ×
              </button>
            </div>

            <p className="text-[11px] leading-snug text-[var(--qs-text-3)]">
              Quick prompts are session assignments for the Orchestrator — like a project brief. They guide how
              Orchestrator receives tasks and replies; they are not inserted into the chat as messages.
            </p>

            <div className="flex flex-col gap-1.5">
              <label htmlFor={labelId} className="text-[10px] uppercase tracking-widest text-[var(--qs-text-3)]">
                Name <span className="normal-case text-[10px] text-[var(--qs-text-3)]">({labelLeft} left)</span>
              </label>
              <input
                id={labelId}
                ref={labelInputRef}
                type="text"
                maxLength={LABEL_MAX}
                value={draftLabel}
                onChange={(e) => setDraftLabel(e.target.value.slice(0, LABEL_MAX))}
                placeholder="e.g. Daily sync"
                className="qs-input rounded-md px-3 py-2 text-[13px]"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor={textId} className="text-[10px] uppercase tracking-widest text-[var(--qs-text-3)]">
                Assignment brief for Orchestrator
              </label>
              <textarea
                id={textId}
                value={draftText}
                onChange={(e) => setDraftText(e.target.value)}
                rows={4}
                placeholder="Describe how Orchestrator should behave in this chat — tone, format, priorities…"
                className="qs-input min-h-[100px] resize-y rounded-md px-3 py-2 text-[13px] leading-snug"
              />
            </div>

            {error ? (
              <p className="rounded border border-[var(--qs-red)]/45 bg-[var(--qs-red)]/10 px-3 py-1.5 text-[11px] text-[var(--qs-red)]">
                {error}
              </p>
            ) : null}

            <div className="v4-filter-dialog-actions flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-end">
              <button
                type="button"
                className="qs-btn qs-btn--ghost h-9 min-w-[100px] justify-center px-3 text-[12px]"
                onClick={closeEdit}
              >
                Cancel
              </button>
              <button
                type="button"
                className="qs-btn qs-btn--primary h-9 min-w-[100px] justify-center px-3 text-[12px]"
                onClick={handleSave}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
