/** Server-only relay for vendor OAuth redirect → FastAPI token exchange. */

import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { QS_ACCESS } from "@/lib/auth-cookies";
import { QS_OAUTH_STATE } from "@/lib/oauth-cookies";
import { backendHiveUrl } from "@/lib/backend-origin";

/**
 * Read Bearer token from Authorization header or HttpOnly dashboard cookie.
 */
export async function resolveDashboardBearer(request: NextRequest): Promise<string | null> {
  const direct = request.headers.get("authorization")?.trim();
  if (direct) {
    return direct;
  }
  try {
    const jar = await cookies();
    const at = jar.get(QS_ACCESS)?.value?.trim();
    if (at) {
      return `Bearer ${at}`;
    }
  } catch {
    /* cookies() only valid in App Router request context */
  }
  return null;
}

/**
 * Validate CSRF cookie vs vendor ``state``, complete token exchange server-side, redirect operator.
 */
export async function relayOAuthCallback(request: NextRequest): Promise<NextResponse> {
  const url = request.nextUrl;
  const state = url.searchParams.get("state");
  const jar = await cookies();
  const cookieState = jar.get(QS_OAUTH_STATE)?.value;

  const failRedirect = (reason: string): NextResponse => {
    const dest = new URL("/connectors", request.url);
    dest.searchParams.set("oauth", "error");
    dest.searchParams.set("reason", reason);
    const out = NextResponse.redirect(dest);
    out.cookies.delete(QS_OAUTH_STATE);
    return out;
  };

  if (!state || !cookieState || state !== cookieState) {
    return failRedirect("csrf_state_mismatch");
  }

  const backendUrl = backendHiveUrl(`/oauth/callback?${url.searchParams.toString()}`);
  const xf = request.headers.get("x-forwarded-for");
  const xr = request.headers.get("x-real-ip");
  const chain = xf?.split(",")[0]?.trim() || xr?.trim();

  let res: Response;
  try {
    res = await fetch(backendUrl, {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...(chain ? { "X-Forwarded-For": chain } : {}),
      },
      cache: "no-store",
    });
  } catch {
    return failRedirect("callback_upstream_unreachable");
  }

  if (!res.ok) {
    return failRedirect("callback_upstream_failed");
  }

  let payload: { redirect_url?: string };
  try {
    payload = (await res.json()) as { redirect_url?: string };
  } catch {
    return failRedirect("callback_bad_payload");
  }

  const nextUrl = payload.redirect_url?.trim();
  if (!nextUrl) {
    return failRedirect("missing_redirect");
  }

  const out = NextResponse.redirect(nextUrl);
  out.cookies.delete(QS_OAUTH_STATE);
  return out;
}
