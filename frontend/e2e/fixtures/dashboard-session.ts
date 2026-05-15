import type { BrowserContext } from "@playwright/test";

import { QS_ACCESS } from "../../lib/auth-cookies";

function base64UrlEncode(input: string): string {
  return Buffer.from(input, "utf-8").toString("base64url");
}

function buildShellJwtStub(): string {
  const now = Math.floor(Date.now() / 1000);
  const header = base64UrlEncode(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = base64UrlEncode(
    JSON.stringify({
      sub: "dash:00000000-0000-4000-8000-000000000001",
      exp: now + 60 * 60 * 8,
      typ: "dashboard_access",
      scope: "dash:read dash:operator",
    }),
  );
  return `${header}.${payload}.playwright-signature`;
}

/**
 * Seeds a minimal dashboard session cookie so middleware allows gated routes.
 *
 * The token is only structurally validated by Next middleware — API calls may still fail without a
 * live hive. Use only for shell / navigation smoke tests.
 */
export async function seedDashboardSessionCookie(context: BrowserContext, baseURL: string): Promise<void> {
  const origin = new URL(baseURL).hostname;
  await context.addCookies([
    {
      name: QS_ACCESS,
      value: buildShellJwtStub(),
      domain: origin,
      path: "/",
      httpOnly: false,
      sameSite: "Lax",
    },
  ]);
}

/**
 * Seeds the dashboard access cookie with an explicit JWT (Phase 4.1 staging only).
 *
 * Never commit real tokens — inject via CI secret or local env for one-off runs.
 */
export async function seedDashboardAccessToken(
  context: BrowserContext,
  baseURL: string,
  accessToken: string,
): Promise<void> {
  const trimmed = accessToken.trim();
  if (!trimmed) {
    throw new Error("seedDashboardAccessToken requires a non-empty access token.");
  }
  const origin = new URL(baseURL).hostname;
  await context.addCookies([
    {
      name: QS_ACCESS,
      value: trimmed,
      domain: origin,
      path: "/",
      httpOnly: false,
      sameSite: "Lax",
    },
  ]);
}
