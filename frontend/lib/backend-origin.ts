/** Build absolute backend URLs for Next.js route handlers (Docker internal network). */

export function backendHiveUrl(restPathUnderV1: string): string {
  const origin = process.env.INTERNAL_BACKEND_ORIGIN?.trim();
  if (!origin) {
    throw new Error("INTERNAL_BACKEND_ORIGIN is not configured.");
  }
  const base = origin.replace(/\/$/, "");
  const sub = restPathUnderV1.startsWith("/") ? restPathUnderV1 : `/${restPathUnderV1}`;
  return `${base}/api/v1${sub}`;
}
