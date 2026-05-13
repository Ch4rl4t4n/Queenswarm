/** Build absolute backend URLs for Next.js route handlers (Docker internal network). */

const DEFAULT_INTERNAL_BACKEND = "http://127.0.0.1:8000";

export function backendHiveUrl(restPathUnderV1: string): string {
  const origin =
    process.env.INTERNAL_BACKEND_ORIGIN?.trim() ||
    /* Docker Compose sets INTERNAL_BACKEND_ORIGIN; local `next dev` often omits it */
    DEFAULT_INTERNAL_BACKEND;
  const base = origin.replace(/\/$/, "");
  const sub = restPathUnderV1.startsWith("/") ? restPathUnderV1 : `/${restPathUnderV1}`;
  return `${base}/api/v1${sub}`;
}
