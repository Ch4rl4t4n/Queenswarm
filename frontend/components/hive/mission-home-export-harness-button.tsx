"use client";

import { Download, Loader2 } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hivePostJson } from "@/lib/api";
import type { LaunchPrepareResult, SkillExportResponse } from "@/lib/hive-types";
import { downloadSkillExportBundle, downloadTextFile } from "@/lib/skill-export-utils";

interface MissionHomeExportHarnessButtonProps {
  limit: number;
  className?: string;
  variant?: "primary" | "ghost";
  "data-testid"?: string;
}

/** POS-X — one-click verified harness export from Mission Home (Personal OS lite). */
export function MissionHomeExportHarnessButton({
  limit,
  className,
  variant = "primary",
  "data-testid": testId = "mission-home-export-harness",
}: MissionHomeExportHarnessButtonProps) {
  const [busy, setBusy] = useState(false);

  const exportSkill = useCallback(async (id: string): Promise<void> => {
    const bundle = await hivePostJson<SkillExportResponse>(`skill-factory/skills/${id}/export`, {});
    await downloadSkillExportBundle(bundle);
  }, []);

  const handleExport = useCallback(async (): Promise<void> => {
    setBusy(true);
    try {
      const result = await hivePostJson<LaunchPrepareResult>("skill-factory/launch/prepare", { limit });
      if (result.exported_count > 0) {
        toast.success(`Exported ${result.exported_count} verified harness pack(s).`, {
          description: result.message,
        });
        downloadTextFile("LAUNCH_CHECKLIST.md", result.checklist_md);
        for (const row of result.exports) {
          await exportSkill(row.skill_id);
        }
      } else {
        toast.info(result.message, {
          description: `${result.tier_counts.draft ?? 0} drafts · ${result.tier_counts.rejected ?? 0} rejected — approve quality forges only.`,
        });
        downloadTextFile("LAUNCH_CHECKLIST.md", result.checklist_md);
      }
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Export batch failed.");
    } finally {
      setBusy(false);
    }
  }, [exportSkill, limit]);

  return (
    <button
      type="button"
      className={
        className ??
        (variant === "primary" ? "qs-btn qs-btn--primary qs-btn--sm inline-flex gap-1" : "qs-btn qs-btn--ghost qs-btn--sm inline-flex gap-1")
      }
      disabled={busy}
      data-testid={testId}
      onClick={() => void handleExport()}
    >
      {busy ? <Loader2 className="size-3.5 animate-spin" aria-hidden /> : <Download className="size-3.5" aria-hidden />}
      Export batch
    </button>
  );
}
