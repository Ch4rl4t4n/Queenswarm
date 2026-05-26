/** Shared dashboard access JWT shape checks (middleware + bearer route). */

function base64UrlDecode(input: string): string | null {
  const normalized = input.replace(/-/g, "+").replace(/_/g, "/");
  const padding = normalized.length % 4;
  const padded = padding ? normalized.padEnd(normalized.length + (4 - padding), "=") : normalized;
  try {
    return atob(padded);
  } catch {
    return null;
  }
}

/** True when token looks like a non-expired dashboard access JWT. */
export function isLikelyValidDashboardAccessToken(raw: string | undefined | null): boolean {
  const trimmed = raw?.trim() ?? "";
  if (!trimmed) {
    return false;
  }
  const parts = trimmed.split(".");
  if (parts.length < 2) {
    return false;
  }
  const payloadRaw = base64UrlDecode(parts[1] ?? "");
  if (!payloadRaw) {
    return false;
  }
  try {
    const payload = JSON.parse(payloadRaw) as { exp?: unknown; sub?: unknown };
    if (typeof payload.exp !== "number") {
      return false;
    }
    if (payload.exp <= Math.floor(Date.now() / 1000)) {
      return false;
    }
    return typeof payload.sub === "string" && payload.sub.trim().length > 0;
  } catch {
    return false;
  }
}
