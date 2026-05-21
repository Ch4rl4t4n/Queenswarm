/** Resolve a short-lived bearer for browser WebSocket subscriptions (HttpOnly cookie → session cache). */

import { markHiveSessionDead } from "@/lib/hive-session-guard";

const CACHE_KEY = "hive_jwt_optional";

function jwtExpiresAtMs(token: string): number | null {
  try {
    const parts = token.split(".");
    if (parts.length < 2) {
      return null;
    }
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/"))) as { exp?: unknown };
    return typeof payload.exp === "number" ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

function cacheToken(token: string): void {
  window.sessionStorage.setItem(CACHE_KEY, token);
}

export function clearHiveBearerCache(): void {
  if (typeof window !== "undefined") {
    window.sessionStorage.removeItem(CACHE_KEY);
  }
}

let refreshFlight: Promise<boolean> | null = null;
let lastRefreshAttemptMs = 0;

async function refreshDashboardSession(force = false): Promise<boolean> {
  const now = Date.now();
  if (!force && now - lastRefreshAttemptMs < 15_000) {
    return refreshFlight ?? Promise.resolve(false);
  }
  if (refreshFlight) {
    return refreshFlight;
  }

  lastRefreshAttemptMs = now;
  refreshFlight = (async () => {
    try {
      const res = await fetch("/api/auth/refresh", { method: "POST", credentials: "include" });
      if (!res.ok) {
        if (res.status === 401) {
          markHiveSessionDead();
        }
        return false;
      }
      clearHiveBearerCache();
      return true;
    } catch {
      return false;
    } finally {
      refreshFlight = null;
    }
  })();

  return refreshFlight;
}

/**
 * Returns a JWT suitable for `?token=` on hive WebSocket URLs.
 *
 * Refreshes the dashboard session when the cached token is missing or near expiry.
 */
export async function resolveHiveBearerToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    return null;
  }

  const cached = window.sessionStorage.getItem(CACHE_KEY)?.trim() ?? "";
  if (cached) {
    const exp = jwtExpiresAtMs(cached);
    if (exp === null || exp > Date.now() + 120_000) {
      return cached;
    }
  }

  async function fetchBearer(): Promise<string | null> {
    try {
      const res = await fetch("/api/auth/bearer", { credentials: "include" });
      if (!res.ok) {
        return null;
      }
      const row = (await res.json()) as { token?: string | null };
      const token = row.token?.trim() ?? "";
      if (token) {
        cacheToken(token);
        return token;
      }
    } catch {
      /* guest WS or offline */
    }
    return null;
  }

  let token = await fetchBearer();
  if (token) {
    return token;
  }

  const refreshed = await refreshDashboardSession();
  if (!refreshed) {
    return null;
  }
  token = await fetchBearer();
  return token;
}

export { refreshDashboardSession };
