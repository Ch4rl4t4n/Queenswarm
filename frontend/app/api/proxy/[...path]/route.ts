import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { attachDashboardTokenCookies } from "@/lib/auth-token-response";
import { QS_ACCESS, QS_REFRESH } from "@/lib/auth-cookies";
import { resolveInternalBackendOrigin } from "@/lib/backend-origin";
import {
  dashboardAccessNeedsRefresh,
  refreshDashboardAccessFromRefreshToken,
} from "@/lib/proxy-session-refresh";

/** Node runtime: cookie bridge + private Docker DNS (`backend`) do not run on Edge. */
export const runtime = "nodejs";

/**
 * Explicit fetch relay to FastAPI (rewrite() to external origins is unreliable for POST bodies).
 * Injects Bearer from HttpOnly session cookie or HIVE_PROXY_JWT when the browser sends no Authorization.
 */
function backendOrigin(): string {
  return resolveInternalBackendOrigin();
}

function buildTarget(request: NextRequest): string {
  const url = request.nextUrl;
  return `${backendOrigin()}${url.pathname.replace("/api/proxy", "/api/v1")}${url.search}`;
}

type AuthSource = "header" | "cookie" | "proxy_jwt" | "none";

interface ResolvedAuthHeader {
  value: string | null;
  source: AuthSource;
  /** When proxy rotated tokens server-side, attach to the outgoing response. */
  refreshedBundle?: { access_token: string; refresh_token: string; expires_in: number };
  /** Refresh cookie present but rotation failed — avoid anonymous backend burst. */
  sessionDead?: boolean;
}

async function resolveAuthHeader(request: NextRequest): Promise<ResolvedAuthHeader> {
  let refreshedBundle: ResolvedAuthHeader["refreshedBundle"];

  try {
    const jar = await cookies();
    let at = jar.get(QS_ACCESS)?.value?.trim() ?? "";
    const rt = jar.get(QS_REFRESH)?.value?.trim() ?? "";

    if (dashboardAccessNeedsRefresh(at) && rt.length >= 16) {
      const bundle = await refreshDashboardAccessFromRefreshToken(rt);
      if (bundle) {
        at = bundle.access_token.trim();
        refreshedBundle = bundle;
      } else {
        return { value: null, source: "none", sessionDead: true };
      }
    }

    if (at) {
      // Prefer HttpOnly session cookie over potentially stale browser Authorization headers.
      return { value: `Bearer ${at}`, source: "cookie", refreshedBundle };
    }
  } catch {
    /* cookies() only valid in App Router request context */
  }

  const direct = request.headers.get("authorization")?.trim() ?? "";
  const directIsBearer = /^bearer\s+/i.test(direct);
  if (direct && directIsBearer) {
    return { value: direct, source: "header" };
  }
  const proxyJwt = process.env.HIVE_PROXY_JWT?.trim();
  if (proxyJwt && proxyJwt !== "unset") {
    return { value: `Bearer ${proxyJwt}`, source: "proxy_jwt" };
  }
  if (direct) {
    // Preserve legacy non-Bearer passthrough only when no dashboard cookie exists.
    return { value: direct, source: "header" };
  }
  return { value: null, source: "none" };
}

async function proxyRequest(request: NextRequest, method: string): Promise<NextResponse> {
  const targetUrl = buildTarget(request);
  const headers = new Headers();

  const resolvedAuth = await resolveAuthHeader(request);
  if (resolvedAuth.sessionDead) {
    return NextResponse.json({ detail: "Session expired — sign in again." }, { status: 401 });
  }
  if (resolvedAuth.value) {
    headers.set("Authorization", resolvedAuth.value);
  }

  const xff = request.headers.get("x-forwarded-for");
  if (xff?.trim()) {
    headers.set("X-Forwarded-For", xff.trim());
  }
  const xrip = request.headers.get("x-real-ip");
  if (xrip?.trim()) {
    headers.set("X-Real-IP", xrip.trim());
  }
  const xfProto = request.headers.get("x-forwarded-proto");
  if (xfProto?.trim()) {
    headers.set("X-Forwarded-Proto", xfProto.trim());
  }
  const xfHost = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  if (xfHost?.trim()) {
    headers.set("X-Forwarded-Host", xfHost.trim());
  }

  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("Content-Type", contentType);
  }
  const accept = request.headers.get("accept");
  if (accept) {
    headers.set("Accept", accept);
  }

  const init: RequestInit = {
    method,
    headers,
  };

  if (method !== "GET" && method !== "HEAD") {
    const body = await request.arrayBuffer();
    if (body.byteLength > 0) {
      init.body = body;
    }
  }

  let upstream: Response;
  try {
    upstream = await fetch(targetUrl, init);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ detail: `proxy_upstream_unreachable: ${msg}` }, { status: 502 });
  }

  const outHeaders = new Headers();
  const uct = upstream.headers.get("content-type");
  if (uct) {
    outHeaders.set("Content-Type", uct);
  }

  const payload = upstream.status === 204 ? null : await upstream.arrayBuffer();
  const response = new NextResponse(payload, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: outHeaders,
  });
  if (resolvedAuth.refreshedBundle) {
    attachDashboardTokenCookies(response, resolvedAuth.refreshedBundle);
  }
  /**
   * Do not clear auth cookies here — the browser client refreshes tokens on 401 via /api/auth/refresh.
   * Clearing cookies on the first expired access token logged users out mid-session (Ballroom voice/chat).
   */
  return response;
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  return proxyRequest(request, "GET");
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  return proxyRequest(request, "POST");
}

export async function PATCH(request: NextRequest): Promise<NextResponse> {
  return proxyRequest(request, "PATCH");
}

export async function PUT(request: NextRequest): Promise<NextResponse> {
  return proxyRequest(request, "PUT");
}

export async function DELETE(request: NextRequest): Promise<NextResponse> {
  return proxyRequest(request, "DELETE");
}
