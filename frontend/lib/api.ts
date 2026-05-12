/**
 * Typed-ish fetch wrapper for `/api/proxy`, which relays to `{INTERNAL_BACKEND_ORIGIN}/api/v1/...`.
 * Use credentials so the dashboard JWT cookie reaches the relay.
 */

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
  const res = await fetch(url, {
    credentials: "include",
    cache: "no-store",
    ...init,
  });
  const body = await parseBody(res);

  if (!res.ok) {
    const detail = detailFromBody(body);
    throw new HiveApiError(
      detail ?? (res.statusText || `HTTP ${res.status}`),
      res.status,
      body,
    );
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return body as T;
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
