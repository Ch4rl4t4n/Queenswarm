/** Utilities for Research Brief Export Factory bundles. */

export interface ResearchBriefExportFile {
  path: string;
  content: string;
}

export interface ResearchBriefExportMeta {
  slug: string;
  title: string;
  suggested_price_eur_cents: number;
}

export interface ResearchBriefExportResponse {
  meta: ResearchBriefExportMeta;
  files: ResearchBriefExportFile[];
}

export function downloadTextFile(filename: string, content: string, mime = "text/plain;charset=utf-8"): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function downloadResearchBriefExportBundle(bundle: ResearchBriefExportResponse): Promise<void> {
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
