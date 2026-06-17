"use client";

import { Loader2, Tag } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveDelete, hiveGet, hivePostJson } from "@/lib/api";
import type { MemoryProjectTagsPayload } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

/** MEM5 — Client/project memory tags + active recall slice filter. */
export function MemoryProjectTagsPanel(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<MemoryProjectTagsPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [label, setLabel] = useState("");
  const [kind, setKind] = useState<"client" | "project">("project");

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<MemoryProjectTagsPayload>("memory/curated/project-tags");
      setSnapshot(data);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Memory tags unavailable.");
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const toggleFilter = useCallback(
    async (tagId: string) => {
      if (!snapshot) return;
      const active = new Set(snapshot.active_filter_tag_ids ?? []);
      if (active.has(tagId)) {
        active.delete(tagId);
      } else {
        active.add(tagId);
      }
      setBusy(true);
      try {
        await hivePostJson("memory/curated/project-tags/active-filter", {
          tag_ids: [...active],
        });
        await reload();
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Filter update failed.");
      } finally {
        setBusy(false);
      }
    },
    [reload, snapshot],
  );

  const createTag = useCallback(async () => {
    const trimmed = label.trim();
    if (trimmed.length < 2) return;
    setBusy(true);
    try {
      await hivePostJson("memory/curated/project-tags", { label: trimmed, kind });
      setLabel("");
      await reload();
      toast.success("Memory tag saved.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Could not save tag.");
    } finally {
      setBusy(false);
    }
  }, [kind, label, reload]);

  const removeTag = useCallback(
    async (tagId: string) => {
      setBusy(true);
      try {
        await hiveDelete(`memory/curated/project-tags/${tagId}`);
        await reload();
        toast.success("Tag removed.");
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Delete failed.");
      } finally {
        setBusy(false);
      }
    },
    [reload],
  );

  if (loading && !snapshot) {
    return (
      <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
        <Loader2 className="size-4 animate-spin" aria-hidden /> Loading memory tags…
      </p>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <V4Card className="border-pollen/25" data-testid="memory-project-tags-panel">
      <V4CardHeader
        leadingIcon={Tag}
        leadingIconTone="gold"
        title="Client / project memory tags"
        description="GBrain-style company brain slices — filter cited recall to tagged hive memory."
        hint={sectionHintNode("knowledgeMemoryProjectTags")}
        actions={
          snapshot.filter_active ? (
            <V4Badge tone="warn">slice active</V4Badge>
          ) : (
            <V4Badge tone="info">all memory</V4Badge>
          )
        }
      />

      <div className="flex flex-wrap gap-2">
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Acme Corp or Q2 Launch"
          className="qs-input min-w-[180px] flex-1"
          aria-label="New memory tag label"
        />
        <select
          value={kind}
          onChange={(e) => setKind(e.target.value as "client" | "project")}
          className="qs-input"
          aria-label="Tag kind"
        >
          <option value="client">Client</option>
          <option value="project">Project</option>
        </select>
        <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" disabled={busy} onClick={() => void createTag()}>
          Add tag
        </button>
      </div>

      {snapshot.tags.length === 0 ? (
        <p className="mt-3 text-sm text-(--qs-text-3)">{snapshot.operator_hint}</p>
      ) : (
        <ul className="mt-3 flex flex-wrap gap-2">
          {snapshot.tags.map((tag) => {
            const active = snapshot.active_filter_tag_ids?.includes(tag.id);
            return (
              <li key={tag.id}>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void toggleFilter(tag.id)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-xs transition-colors",
                    active
                      ? "border-pollen bg-pollen/15 text-pollen"
                      : "border-(--qs-border) bg-black/20 text-(--qs-text-2) hover:border-cyan/40",
                  )}
                  data-testid={`memory-tag-${tag.id}`}
                >
                  <span className="font-medium">{tag.label}</span>
                  <span className="ml-1 text-[10px] uppercase text-(--qs-text-4)">{tag.kind}</span>
                  <span className="ml-1 font-mono text-[10px] text-cyan">{tag.knowledge_count}</span>
                </button>
                <button
                  type="button"
                  className="ml-1 text-[10px] text-(--qs-text-4) hover:text-(--qs-red)"
                  disabled={busy}
                  onClick={() => void removeTag(tag.id)}
                  aria-label={`Delete ${tag.label}`}
                >
                  ×
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <p className="mt-3 text-xs text-(--qs-text-3)">{snapshot.operator_hint}</p>
    </V4Card>
  );
}
