/**
 * Axios client for Phase G pages that explicitly attach `Authorization`.
 * Proxied hive traffic still prefers {@link hiveFetch} + HttpOnly cookies.
 */

import axios, { type AxiosInstance } from "axios";

/** Browser-only token slot used by ballroom / legacy demos. */
const QS_TOKEN_KEY = "qs_token";

export function hiveAxios(baseURL?: string): AxiosInstance {
  const root = typeof window !== "undefined" ? window.location.origin : "";
  const normalizedBase =
    baseURL ??
    process.env.NEXT_PUBLIC_API_AXIOS_BASE ??
    (process.env.NEXT_PUBLIC_API_BASE && process.env.NEXT_PUBLIC_API_BASE.startsWith("http")
      ? process.env.NEXT_PUBLIC_API_BASE
      : `${root}/api/v1`);

  const client = axios.create({
    baseURL: normalizedBase.replace(/\/$/, ""),
    timeout: 60_000,
    withCredentials: true,
  });

  client.interceptors.request.use(async (config) => {
    if (typeof window === "undefined") {
      return config;
    }
    let bearer = window.localStorage.getItem(QS_TOKEN_KEY);
    if (!bearer) {
      try {
        const res = await fetch("/api/auth/bearer", { credentials: "include" });
        if (res.ok) {
          const row = (await res.json()) as { token?: string | null };
          if (row.token) {
            bearer = row.token;
          }
        }
      } catch {
        /* ignore */
      }
    }
    if (bearer) {
      config.headers.Authorization = `Bearer ${bearer}`;
    }
    return config;
  });

  client.interceptors.response.use(
    (r) => r,
    (err) => {
      const status = err?.response?.status as number | undefined;
      if (status === 401 && typeof window !== "undefined") {
        window.localStorage.removeItem(QS_TOKEN_KEY);
        const next = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.assign(`/login?next=${next}`);
      }
      return Promise.reject(err);
    },
  );

  return client;
}
