/** Utilities for Recipe → skill export bundles (`POST /recipes/{id}/export-skill`). */

import type { SkillExportFile, SkillExportResponse } from "@/lib/hive-types";

/**
 * Trigger browser download for a UTF-8 text file.
 */
export function downloadTextFile(filename: string, content: string, mime = "text/plain;charset=utf-8"): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

/**
 * Download each file in an export bundle (staggered to avoid popup blockers).
 */
export async function downloadSkillExportBundle(bundle: SkillExportResponse): Promise<void> {
  for (let i = 0; i < bundle.files.length; i += 1) {
    const file = bundle.files[i];
    if (!file) continue;
    const leaf = file.path.split("/").pop() ?? file.path;
    downloadTextFile(`${bundle.meta.slug}-${leaf}`, file.content);
    if (i < bundle.files.length - 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 120));
    }
  }
}

export function skillMdFromBundle(bundle: SkillExportResponse): SkillExportFile | undefined {
  return bundle.files.find((f) => f.path.endsWith("SKILL.md"));
}

export function hiveMdFromBundle(bundle: SkillExportResponse): SkillExportFile | undefined {
  return bundle.files.find((f) => f.path.endsWith("HIVE.md"));
}
