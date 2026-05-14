import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { QS_ACCESS } from "@/lib/auth-cookies";
import { resolveInternalBackendOrigin } from "@/lib/backend-origin";

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

async function resolveAuthHeader(request: NextRequest): Promise<string | null> {
  const direct = request.headers.get("authorization");
  if (direct?.trim()) {
    return direct.trim();
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
  const proxyJwt = process.env.HIVE_PROXY_JWT?.trim();
  if (proxyJwt && proxyJwt !== "unset") {
    return `Bearer ${proxyJwt}`;
  }
  return null;
}

async function proxyRequest(request: NextRequest, method: string): Promise<NextResponse> {
  const targetUrl = buildTarget(request);
  const headers = new Headers();

  const auth = await resolveAuthHeader(request);
  if (auth) {
    headers.set("Authorization", auth);
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
  return new NextResponse(payload, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: outHeaders,
  });
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
