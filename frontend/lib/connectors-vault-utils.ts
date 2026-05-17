/**
 * Shared helpers for connector vault / handshake flows (UI only).
 */

/** Normalize connector slugs before vault rows or ping paths. */
export function normalizeVaultSlug(raw: string): string {
  return raw.trim().toLowerCase();
}

/** Accept only HTTPS URLs for invoke-probe (matches backend AnyHttpUrl expectation). */
export function isHttpsProbeUrl(raw: string): boolean {
  const s = raw.trim();
  if (!s) {
    return false;
  }
  try {
    const u = new URL(s);
    return u.protocol === "https:";
  } catch {
    return false;
  }
}
