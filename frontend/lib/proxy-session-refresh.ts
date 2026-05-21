import "server-only";

import { hiveRelayPost, hiveRelayReadJson, hiveRelayTargetUrl } from "@/lib/backend-relay";

interface TokenUpstream {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

function decodeJwtExpSec(token: string): number | null {
  const parts = token.split(".");
  if (parts.length < 2) {
    return null;
  }
  const normalized = parts[1].replace(/-/g, "+").replace(/_/g, "/");
  const padding = normalized.length % 4;
  const padded = padding ? normalized.padEnd(normalized.length + (4 - padding), "=") : normalized;
  try {
    const payload = JSON.parse(Buffer.from(padded, "base64").toString("utf-8")) as { exp?: unknown };
    return typeof payload.exp === "number" ? payload.exp : null;
  } catch {
    return null;
  }
}

/** True when access JWT is missing or expires within the skew window. */
export function dashboardAccessNeedsRefresh(accessToken: string | undefined, skewSec = 90): boolean {
  if (!accessToken?.trim()) {
    return true;
  }
  const exp = decodeJwtExpSec(accessToken.trim());
  if (exp === null) {
    return true;
  }
  return exp <= Math.floor(Date.now() / 1000) + skewSec;
}

/**
 * Rotate dashboard tokens server-side (proxy path when browser cookie expired).
 *
 * @returns Fresh token bundle or null when refresh is rejected.
 */
export async function refreshDashboardAccessFromRefreshToken(
  refreshToken: string,
): Promise<TokenUpstream | null> {
  return refreshDashboardAccessSingleFlight(refreshToken);
}

let refreshFlight: Promise<TokenUpstream | null> | null = null;
let refreshFlightKey = "";

async function refreshDashboardAccessSingleFlight(refreshToken: string): Promise<TokenUpstream | null> {
  const key = refreshToken.slice(0, 24);
  if (refreshFlight && refreshFlightKey === key) {
    return refreshFlight;
  }
  refreshFlightKey = key;
  refreshFlight = (async () => {
    try {
      return await refreshDashboardAccessFromRefreshTokenRaw(refreshToken);
    } finally {
      refreshFlight = null;
      refreshFlightKey = "";
    }
  })();
  return refreshFlight;
}

async function refreshDashboardAccessFromRefreshTokenRaw(
  refreshToken: string,
): Promise<TokenUpstream | null> {
  const path = "/auth/refresh";
  const targetUrl = hiveRelayTargetUrl(path);

  let upstream: Response;
  try {
    upstream = await hiveRelayPost(path, { refresh_token: refreshToken });
  } catch {
    return null;
  }

  const parsed = await hiveRelayReadJson<TokenUpstream & { detail?: unknown }>(upstream, targetUrl);
  if (!parsed.ok || !upstream.ok) {
    return null;
  }
  const payload = parsed.data;
  if (!payload.access_token?.trim() || !payload.refresh_token?.trim()) {
    return null;
  }
  return payload;
}
