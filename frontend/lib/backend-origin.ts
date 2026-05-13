/** Build absolute backend URLs for Next.js route handlers (Docker internal network). */

/** Local Next dev defaults to loopback — Compose overrides via INTERNAL_BACKEND_ORIGIN. */
export const DEFAULT_INTERNAL_BACKEND = "http://127.0.0.1:8000";

/**
 * Canonical origin for relaying `/api/proxy/*` and server-side hive fetch.
 * Must match docker-compose `INTERNAL_BACKEND_ORIGIN` when running in the stack.
 */
export function resolveInternalBackendOrigin(): string {
  const raw =
    process.env.INTERNAL_BACKEND_ORIGIN?.trim() ||
    /* Docker Compose sets INTERNAL_BACKEND_ORIGIN; local `next dev` often omits it */
    DEFAULT_INTERNAL_BACKEND;
  return raw.replace(/\/$/, "");
}

export function backendHiveUrl(restPathUnderV1: string): string {
  const base = resolveInternalBackendOrigin();
  const sub = restPathUnderV1.startsWith("/") ? restPathUnderV1 : `/${restPathUnderV1}`;
  return `${base}/api/v1${sub}`;
}
