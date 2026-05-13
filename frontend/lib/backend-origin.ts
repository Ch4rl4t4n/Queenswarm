/** Build absolute backend URLs for Next.js route handlers (Docker internal network). */

/** Local Next dev defaults to loopback — Compose overrides via INTERNAL_BACKEND_ORIGIN. */
export const DEFAULT_INTERNAL_BACKEND = "http://127.0.0.1:8000";

/**
 * Canonical origin for relaying `/api/proxy/*` and server-side hive fetch.
 * Must match docker-compose `INTERNAL_BACKEND_ORIGIN` when running in the stack.
 */
export function resolveInternalBackendOrigin(): string {
  let raw =
    process.env.INTERNAL_BACKEND_ORIGIN?.trim() ||
    /* Docker Compose sets INTERNAL_BACKEND_ORIGIN; local `next dev` often omits it */
    DEFAULT_INTERNAL_BACKEND;
  raw = raw.replace(/\/+$/, "");
  /* Proxy route already prefixes `/api/v1` — strip accidental suffix so we never hit `/api/v1/api/v1/...`. */
  raw = raw.replace(/\/?api\/v1$/i, "").replace(/\/+$/, "");
  return raw.trim() !== "" ? raw : DEFAULT_INTERNAL_BACKEND;
}

export function backendHiveUrl(restPathUnderV1: string): string {
  const base = resolveInternalBackendOrigin();
  const sub = restPathUnderV1.startsWith("/") ? restPathUnderV1 : `/${restPathUnderV1}`;
  return `${base}/api/v1${sub}`;
}
