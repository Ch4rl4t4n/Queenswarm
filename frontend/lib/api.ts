/**
 * Typed-ish fetch wrapper for `/api/proxy`, which relays to `{INTERNAL_BACKEND_ORIGIN}/api/v1/...`.
 * Use credentials so the dashboard JWT cookie reaches the relay.
 * On 401, silently refreshes the session once and retries.
 * On 429 / 502 / 503, retries with backoff (respects ``Retry-After`` for rate limits).
 */

import { clearHiveBearerCache, refreshDashboardSession } from "@/lib/hive-bearer-token";
import { notifyHiveApiRateLimitChanged } from "@/lib/hive-api-rate-limit-bus";
import { isHiveSessionDead, markHiveSessionDead } from "@/lib/hive-session-guard";

export class HiveApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body: unknown,
  ) {
    super(message);
    this.name = "HiveApiError";
  }

  repr(): string {
    return `${this.name}(status=${this.status}, message=${JSON.stringify(this.message)})`;
  }
}

/** True when the API rejected the call due to sliding-window rate limiting. */
export function isRateLimitError(error: unknown): error is HiveApiError {
  return error instanceof HiveApiError && error.status === 429;
}

let rateLimitPauseUntilMs = 0;
let lastRateLimitToastMs = 0;

/** True while the client is backing off after a 429 (pollers should pause). */
export function isHiveApiRateLimited(): boolean {
  return Date.now() < rateLimitPauseUntilMs;
}

function registerRateLimitPause(retryMs: number): void {
  rateLimitPauseUntilMs = Math.max(rateLimitPauseUntilMs, Date.now() + Math.max(retryMs, 8000));
  notifyHiveApiRateLimitChanged();
}

const inFlightGet = new Map<string, Promise<unknown>>();

function dedupeGet<T>(url: string, run: () => Promise<T>): Promise<T> {
  const existing = inFlightGet.get(url) as Promise<T> | undefined;
  if (existing) {
    return existing;
  }
  const flight = run().finally(() => {
    inFlightGet.delete(url);
  });
  inFlightGet.set(url, flight);
  return flight;
}

/** Operator-facing copy for toast / inline alerts. */
export function hiveApiUserMessage(error: unknown): string {
  if (error instanceof HiveApiError) {
    if (error.status === 429) {
      return "Rate limit reached — wait a few seconds and try again.";
    }
    if (error.status === 401) {
      return "Session vypršala — prihlás sa znova.";
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed.";
}

function retryAfterMs(res: Response): number {
  const raw = res.headers.get("retry-after");
  if (!raw) {
    return 2000;
  }
  const seconds = Number.parseInt(raw, 10);
  if (Number.isFinite(seconds) && seconds > 0) {
    return Math.min(seconds, 8) * 1000;
  }
  return 2000;
}

async function notifyRateLimitToast(): Promise<void> {
  if (typeof window === "undefined") {
    return;
  }
  const now = Date.now();
  if (now - lastRateLimitToastMs < 15_000) {
    return;
  }
  lastRateLimitToastMs = now;
  const { toast } = await import("sonner");
  toast.error("Rate limit reached", {
    description: "Too many requests — wait a moment, then retry.",
    duration: 7000,
  });
}

const PROXY_PREFIX = "/api/proxy";

function normalizeV1RelativePath(subpath: string): string {
  let p = subpath.trim();
  p = p.replace(/^\/?api\/v1\/?/, "");
  return p.startsWith("/") ? p.slice(1) : p;
}

async function parseBody(res: Response): Promise<unknown> {
  const ct = res.headers.get("content-type") ?? "";
  if (!ct.includes("application/json")) {
    return await res.text();
  }
  try {
    return await res.json();
  } catch {
    return null;
  }
}

function detailFromBody(body: unknown): string | null {
  if (typeof body !== "object" || body === null) {
    return null;
  }
  if ("detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") {
      return d;
    }
    return JSON.stringify(d);
  }
  return null;
}

/**
 * Proxied JSON request to `/api/v1/<path>` on the backend.
 *
 * @param subpath Relative path without leading slash, e.g. `dashboard/summary`
 * @throws HiveApiError on non-OK responses (body parsed when JSON)
 */
export async function hiveFetch<T = unknown>(subpath: string, init?: RequestInit): Promise<T> {
  const path = normalizeV1RelativePath(subpath);
  const url = `${PROXY_PREFIX}/${path}`;
  const method = (init?.method ?? "GET").toUpperCase();

  async function execute(): Promise<T> {
    async function attempt(authRetried: boolean, transientRetries = 0): Promise<T> {
      if (isHiveSessionDead()) {
        throw new HiveApiError("Session vypršala — prihlás sa znova.", 401, {});
      }
      if (isHiveApiRateLimited()) {
        throw new HiveApiError("Rate limit reached — wait a few seconds and try again.", 429, {});
      }

      const res = await fetch(url, {
        credentials: "include",
        cache: "no-store",
        ...init,
      });
      const body = await parseBody(res);

      if (res.status === 401 && !authRetried) {
        const refreshed = await refreshDashboardSession();
        if (refreshed) {
          clearHiveBearerCache();
          return attempt(true, transientRetries);
        }
        markHiveSessionDead();
        throw new HiveApiError("Session vypršala — prihlás sa znova.", 401, body);
      }

      if (res.status === 401 && authRetried) {
        markHiveSessionDead();
        throw new HiveApiError("Session vypršala — prihlás sa znova.", 401, body);
      }

      if ((res.status === 502 || res.status === 503) && transientRetries < 2) {
        await new Promise((resolve) => setTimeout(resolve, 800 * (transientRetries + 1)));
        return attempt(authRetried, transientRetries + 1);
      }

      if (res.status === 429) {
        if (transientRetries < 1) {
          await new Promise((resolve) => setTimeout(resolve, retryAfterMs(res)));
          return attempt(authRetried, transientRetries + 1);
        }
        registerRateLimitPause(retryAfterMs(res));
      }

      if (!res.ok) {
        const detail = detailFromBody(body);
        if (res.status === 429) {
          await notifyRateLimitToast();
        }
        throw new HiveApiError(
          res.status === 429
            ? "Rate limit reached — wait a few seconds and try again."
            : res.status === 401
              ? "Session vypršala — prihlás sa znova."
              : (detail ?? (res.statusText || `HTTP ${res.status}`)),
          res.status,
          body,
        );
      }
      if (res.status === 204) {
        return undefined as T;
      }
      return body as T;
    }

    return attempt(false);
  }

  if (method === "GET") {
    return dedupeGet(url, execute);
  }

  return execute();
}

export function hiveGet<T>(subpath: string, init?: RequestInit): Promise<T> {
  return hiveFetch<T>(subpath, { ...init, method: "GET" });
}

export function hivePostJson<T>(
  subpath: string,
  json: unknown,
  init?: RequestInit,
): Promise<T> {
  return hiveFetch<T>(subpath, {
    ...init,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    body: JSON.stringify(json),
  });
}

export function hivePatchJson<T>(
  subpath: string,
  json: unknown,
  init?: RequestInit,
): Promise<T> {
  return hiveFetch<T>(subpath, {
    ...init,
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    body: JSON.stringify(json),
  });
}

export function hivePutJson<T>(
  subpath: string,
  json: unknown,
  init?: RequestInit,
): Promise<T> {
  return hiveFetch<T>(subpath, {
    ...init,
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    body: JSON.stringify(json),
  });
}

/** Proxied GET for binary / streaming responses — caller checks ``Response.ok``. */
export function hiveFetchRaw(subpath: string, init?: RequestInit): Promise<Response> {
  const path = normalizeV1RelativePath(subpath);
  const url = `${PROXY_PREFIX}/${path}`;
  return fetch(url, {
    credentials: "include",
    cache: "no-store",
    ...init,
  });
}

export function hiveDelete<T>(subpath: string, init?: RequestInit): Promise<T> {
  return hiveFetch<T>(subpath, { ...init, method: "DELETE" });
}

/** Convenience object for callers that prefer a grouped API surface. */
export const hiveApi = {
  get: hiveGet,
  post: hivePostJson,
  patch: hivePatchJson,
  put: hivePutJson,
  delete: hiveDelete,
  fetch: hiveFetch,
  fetchRaw: hiveFetchRaw,
} as const;
