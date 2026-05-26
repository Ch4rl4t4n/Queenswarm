import { NextRequest, NextResponse } from "next/server";

import { QS_OAUTH_STATE } from "@/lib/oauth-cookies";
import { backendHiveUrl } from "@/lib/backend-origin";
import { resolveDashboardBearer } from "@/lib/oauth-callback-server";

export const runtime = "nodejs";

type RouteCtx = { params: Promise<{ provider: string }> };

/**
 * POST begins Authorization Code + PKCE; sets HttpOnly OAuth state cookie before vendor redirect.
 */
export async function POST(request: NextRequest, ctx: RouteCtx): Promise<NextResponse> {
  const { provider } = await ctx.params;
  const cleaned = provider.trim().toLowerCase();
  if (!/^[a-z0-9_]+$/.test(cleaned)) {
    return NextResponse.json({ detail: "invalid_provider" }, { status: 400 });
  }

  const auth = await resolveDashboardBearer(request);
  if (!auth) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const url = backendHiveUrl("/oauth/start");
  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: auth,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ provider: cleaned }),
      cache: "no-store",
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ detail: `oauth_start_unreachable: ${msg}` }, { status: 502 });
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      /* ignore */
    }
    return NextResponse.json({ detail }, { status: res.status });
  }

  const payload = (await res.json()) as { authorization_url?: string; state?: string };
  const authorizationUrl = payload.authorization_url?.trim();
  const state = payload.state?.trim();
  if (!authorizationUrl || !state) {
    return NextResponse.json({ detail: "oauth_start_malformed" }, { status: 502 });
  }

  const out = NextResponse.redirect(authorizationUrl);
  const secure = process.env.NODE_ENV === "production";
  out.cookies.set(QS_OAUTH_STATE, state, {
    httpOnly: true,
    secure,
    sameSite: "lax",
    path: "/",
    maxAge: 600,
  });
  // Hint for browsers that partition cookies on cross-site OAuth round-trips.
  out.headers.set("Cache-Control", "no-store");
  return out;
}
