import { cookies } from "next/headers";

import { resolveInternalBackendOrigin } from "@/lib/backend-origin";
import { QS_ACCESS } from "@/lib/auth-cookies";

const API_PREFIX = "/api/v1";

/**
 * Prefer the Compose-injected hive proxy JWT, then fall back to the operator HttpOnly session
 * cookie so RSC dashboards load after login without requiring ``HIVE_PROXY_JWT``.
 */
async function resolveHiveBearerToken(): Promise<string | null> {
  const proxyJwt = process.env.HIVE_PROXY_JWT?.trim();
  if (proxyJwt && proxyJwt !== "unset") {
    return proxyJwt;
  }
  try {
    const jar = await cookies();
    const sessionAt = jar.get(QS_ACCESS)?.value?.trim();
    if (sessionAt) {
      return sessionAt;
    }
  } catch {
    /* ``cookies()`` is only valid in a React Server Component / Route Handler request. */
  }
  return null;
}

async function hiveServerFetch(path: string, init?: RequestInit): Promise<Response> {
  const origin = resolveInternalBackendOrigin();

  const bearer = await resolveHiveBearerToken();
  if (!bearer) {
    throw new Error("Hive bearer unavailable — configure HIVE_PROXY_JWT or ensure the dashboard session cookie is present.");
  }

  const clean = path.startsWith("/") ? path : `/${path}`;
  const url = `${origin}${API_PREFIX}${clean}`;
  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${bearer}`);
  return fetch(url, {
    ...init,
    headers,
    cache: "no-store",
  });
}

export async function hiveServerJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await hiveServerFetch(path, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Hive API ${path} → ${res.status}: ${text.slice(0, 300)}`);
  }
  return res.json() as Promise<T>;
}

export async function hiveServerRawJson<T>(path: string, init?: RequestInit): Promise<T | null> {
  try {
    return await hiveServerJson<T>(path, init);
  } catch {
    return null;
  }
}
