/** Utilities for Content Pack Factory export bundles. */

export interface ContentPackExportFile {
  path: string;
  content: string;
}

export interface ContentPackExportMeta {
  pack_id: string;
  slug: string;
  title: string;
  channel: string;
  verified: boolean;
  price_eur_cents: number;
}

export interface ContentPackExportResponse {
  meta: ContentPackExportMeta;
  files: ContentPackExportFile[];
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

export async function downloadContentPackExportBundle(bundle: ContentPackExportResponse): Promise<void> {
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
