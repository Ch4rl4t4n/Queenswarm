/**
 * Typed-ish fetch wrapper for `/api/proxy`, which relays to `{INTERNAL_BACKEND_ORIGIN}/api/v1/...`.
 * Use credentials so the dashboard JWT cookie reaches the relay.
 * On 401, silently refreshes the session once and retries.
 * On 429 / 502 / 503, retries with backoff (respects ``Retry-After`` for rate limits).
 */

import { clearHiveBearerCache, refreshDashboardSession } from "@/lib/hive-bearer-token";

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

/** Operator-facing copy for toast / inline alerts. */
export function hiveApiUserMessage(error: unknown): string {
  if (error instanceof HiveApiError) {
    if (error.status === 429) {
      return "Rate limit reached — wait a few seconds and try again.";
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

  async function attempt(authRetried: boolean, transientRetries = 0): Promise<T> {
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
    }

    if ((res.status === 502 || res.status === 503) && transientRetries < 2) {
      await new Promise((resolve) => setTimeout(resolve, 800 * (transientRetries + 1)));
      return attempt(authRetried, transientRetries + 1);
    }

    if (res.status === 429 && transientRetries < 2) {
      await new Promise((resolve) => setTimeout(resolve, retryAfterMs(res)));
      return attempt(authRetried, transientRetries + 1);
    }

    if (!res.ok) {
      const detail = detailFromBody(body);
      if (res.status === 429) {
        await notifyRateLimitToast();
      }
      throw new HiveApiError(
        res.status === 429
          ? "Rate limit reached — wait a few seconds and try again."
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
