const API_PREFIX = "/api/v1";

async function hiveServerFetch(path: string, init?: RequestInit): Promise<Response> {
  const origin = process.env.INTERNAL_BACKEND_ORIGIN;
  const token = process.env.HIVE_PROXY_JWT;
  if (!origin || !token || token === "unset") {
    throw new Error(
      "Missing INTERNAL_BACKEND_ORIGIN or HIVE_PROXY_JWT (set DASHBOARD_JWT in Compose for the dashboard token).",
    );
  }
  const clean = path.startsWith("/") ? path : `/${path}`;
  const url = `${origin}${API_PREFIX}${clean}`;
  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${token}`);
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
