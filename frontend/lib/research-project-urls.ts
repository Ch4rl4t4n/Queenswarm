/** POS-J4 — Client-side URL dedupe mirror for Research Bee project batch. */

export function normalizeResearchUrl(url: string): string {
  try {
    const parsed = new URL(url.trim());
    const host = parsed.hostname.toLowerCase().replace(/^www\./, "");
    const path = parsed.pathname.replace(/\/$/, "") || "/";
    return `${host}${path}`;
  } catch {
    return url.trim().toLowerCase();
  }
}

export function dedupeResearchProjectUrls(sourceUrls: readonly string[], max = 8): string[] {
  const seen = new Set<string>();
  const ranked: Array<{ score: number; url: string }> = [];
  for (const raw of sourceUrls) {
    const url = raw.trim();
    if (!url) {
      continue;
    }
    const key = normalizeResearchUrl(url);
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    ranked.push({ score: key.length + (url.endsWith("/") ? 10 : 0), url });
  }
  ranked.sort((a, b) => a.score - b.score);
  return ranked.slice(0, max).map((row) => row.url);
}

export function parseResearchProjectUrls(text: string, max = 8): string[] {
  const lines = text.split(/\r?\n/);
  return dedupeResearchProjectUrls(lines, max);
}
