/** Client-side publish media URL safety — mirrors backend publish_media rules. */

export type PublishMediaKind = "image" | "video" | "unknown";

const VIDEO_EXTENSIONS = new Set([".mp4", ".webm", ".mov", ".m4v", ".mkv"]);
const IMAGE_EXTENSIONS = new Set([".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"]);

function pathExtension(url: string): string {
  try {
    const path = new URL(url).pathname.toLowerCase();
    const dot = path.lastIndexOf(".");
    return dot >= 0 ? path.slice(dot) : "";
  } catch {
    return "";
  }
}

/** True when URL is safe to embed in img/video (HTTPS, no credentials). */
export function isSafePublishMediaUrl(url: string | null | undefined): boolean {
  const text = String(url ?? "").trim();
  if (!text || text.length > 500) return false;
  try {
    const parsed = new URL(text);
    if (parsed.protocol !== "https:") return false;
    if (parsed.username || parsed.password) return false;
    const host = parsed.hostname.toLowerCase();
    if (!host || host === "localhost" || host.startsWith("127.")) return false;
    return true;
  } catch {
    return false;
  }
}

export function classifyPublishMediaUrl(url: string | null | undefined): PublishMediaKind | null {
  const text = String(url ?? "").trim();
  if (!text) return null;
  const ext = pathExtension(text);
  if (VIDEO_EXTENSIONS.has(ext)) return "video";
  if (IMAGE_EXTENSIONS.has(ext)) return "image";
  return "unknown";
}

/** Prefer video element when channel is tiktok or URL looks like video. */
export function resolvePublishMediaPreviewMode(
  url: string | null | undefined,
  channel?: string | null,
): "image" | "video" | "link" {
  if (!isSafePublishMediaUrl(url)) return "link";
  const kind = classifyPublishMediaUrl(url);
  const ch = String(channel ?? "").toLowerCase();
  if (ch === "tiktok" || kind === "video") return "video";
  if (kind === "image" || kind === "unknown") return "image";
  return "link";
}
