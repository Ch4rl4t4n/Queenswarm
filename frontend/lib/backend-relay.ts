import { NextResponse } from "next/server";

import { backendHiveUrl } from "@/lib/backend-origin";

/** Time budget for hive API calls from Route Handlers (login, refresh, 2FA). */
const RELAY_TIMEOUT_MS = 30_000;

/**
 * POST JSON to `{INTERNAL_BACKEND_ORIGIN}/api/v1/{pathUnderV1}`.
 *
 * @param pathUnderV1 Path fragment after `/api/v1`, leading slash optional (e.g. `/auth/login`).
 * @param jsonBody Serializable request body.
 * @throws When the TCP/fetch layer fails before an HTTP status is produced.
 */
export async function hiveRelayPost(pathUnderV1: string, jsonBody: unknown): Promise<Response> {
  const url = backendHiveUrl(pathUnderV1);
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(jsonBody),
    cache: "no-store",
    signal: AbortSignal.timeout(RELAY_TIMEOUT_MS),
  });
}

/** Current URL passed to callers for diagnostics. */
export function hiveRelayTargetUrl(pathUnderV1: string): string {
  return backendHiveUrl(pathUnderV1);
}

/**
 * Parse upstream body as JSON; empty body becomes `{}`.
 *
 * @returns Either parsed data or a ready `NextResponse` for the client when body is invalid JSON.
 */
export async function hiveRelayReadJson<T>(
  upstream: Response,
  relayTargetUrl: string,
): Promise<{ ok: true; data: T } | { ok: false; response: NextResponse }> {
  const raw = await upstream.text();
  const snippet = raw.trim().slice(0, 600);
  if (!raw.trim()) {
    return { ok: true, data: {} as T };
  }
  try {
    return { ok: true, data: JSON.parse(raw) as T };
  } catch {
    console.error("[hive-relay] upstream non-json", { relayTargetUrl, snippet });
    const isDev = process.env.NODE_ENV === "development";
    return {
      ok: false,
      response: NextResponse.json(
        {
          detail: isDev
            ? `Upstream returned non-JSON. Check that the API is running and URL is correct.`
            : "Auth service misconfigured.",
          ...(isDev ? { relay_target: relayTargetUrl, body_preview: snippet } : {}),
        },
        { status: 502 },
      ),
    };
  }
}

/** Map fetch/timeout errors to a 503 the UI can surface. */
export function hiveRelayNetworkErrorResponse(error: unknown, relayTargetUrl: string): NextResponse {
  const isDev = process.env.NODE_ENV === "development";
  const msg = error instanceof Error ? error.message : String(error);
  console.error("[hive-relay] network error", { relayTargetUrl, message: msg });
  return NextResponse.json(
    {
      detail: isDev
        ? `Cannot reach API (${msg}). Start backend on port 8000 or set INTERNAL_BACKEND_ORIGIN.`
        : "Auth relay unavailable.",
      ...(isDev ? { relay_target: relayTargetUrl } : {}),
    },
    { status: 503 },
  );
}
