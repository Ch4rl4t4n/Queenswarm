import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { QS_ACCESS, QS_REFRESH } from "@/lib/auth-cookies";
import { isLikelyValidDashboardAccessToken } from "@/lib/dashboard-access-jwt";

function controlPlaneHome(): string {
  const singleAdmin = process.env.NEXT_PUBLIC_SINGLE_ADMIN_MODE;
  if (singleAdmin !== undefined) {
    const normSingleAdmin = singleAdmin.trim().toLowerCase();
    if (["1", "true", "yes", "on"].includes(normSingleAdmin)) {
      return "/agentic-os";
    }
  }
  const raw = process.env.NEXT_PUBLIC_OPERATOR_CONTROL_PLANE_ENABLED;
  if (raw === undefined) {
    return "/agentic-os";
  }
  const norm = raw.trim().toLowerCase();
  if (["0", "false", "no", "off"].includes(norm)) {
    return "/dashboard";
  }
  return "/agentic-os";
}

/** Paths that bypass auth gates; gated routes rely on HttpOnly ``qs_dashboard_at`` cookie (see ``attachDashboardTokenCookies``). */

const PUBLIC_PREFIXES = ["/login", "/verify-2fa", "/terms", "/privacy", "/data-deletion", "/health", "/offline", "/magnet", "/transparency"];

/** PWA shell assets — no auth redirect (mobile/tablet install + offline fallback). */
const PUBLIC_EXACT = new Set([
  "/manifest.webmanifest",
  "/manifest",
  "/sw.js",
  "/icon",
  "/apple-icon",
]);

function isLikelyValidDashboardJwt(raw: string): boolean {
  return isLikelyValidDashboardAccessToken(raw);
}

function hasRefreshSession(request: NextRequest): boolean {
  const refresh = request.cookies.get(QS_REFRESH)?.value?.trim() ?? "";
  return refresh.length >= 16;
}

function buildNextTarget(url: URL): string {
  const pathname = url.pathname || "/";
  const query = url.search || "";
  return `${pathname}${query}`;
}

export function middleware(request: NextRequest) {
  if (process.env.E2E_PHASE70_NAV === "1" || process.env.E2E_BYPASS_AUTH === "1") {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;
  /** HttpOnly dashboard cookie preferred; legacy ``qs_token`` mirrors Bearer for some clients. */
  const access = request.cookies.get(QS_ACCESS)?.value ?? request.cookies.get("qs_token")?.value;
  const refreshSession = hasRefreshSession(request);
  const sessionExpiredReason = request.nextUrl.searchParams.get("reason") === "session_expired";

  if (
    sessionExpiredReason &&
    (pathname.startsWith("/login") || pathname.startsWith("/verify-2fa"))
  ) {
    return NextResponse.next();
  }

  if (
    access &&
    isLikelyValidDashboardJwt(access) &&
    (pathname.startsWith("/login") || pathname.startsWith("/verify-2fa"))
  ) {
    return NextResponse.redirect(new URL(controlPlaneHome(), request.url));
  }

  if (pathname === "/dashboard" || pathname.startsWith("/dashboard/")) {
    const home = controlPlaneHome();
    if (home === "/agentic-os") {
      return NextResponse.redirect(new URL("/agentic-os", request.url));
    }
  }

  if (pathname.startsWith("/api/auth")) {
    return NextResponse.next();
  }
  if (pathname.startsWith("/api/")) {
    return NextResponse.next();
  }
  if (PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
    return NextResponse.next();
  }
  if (PUBLIC_EXACT.has(pathname)) {
    return NextResponse.next();
  }

  if (access && !isLikelyValidDashboardJwt(access)) {
    if (refreshSession) {
      return NextResponse.next();
    }
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", buildNextTarget(request.nextUrl));
    const response = NextResponse.redirect(url);
    response.cookies.delete(QS_ACCESS);
    response.cookies.delete("qs_token");
    response.cookies.delete(QS_REFRESH);
    return response;
  }

  if (!access) {
    if (refreshSession) {
      return NextResponse.next();
    }
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", buildNextTarget(request.nextUrl));
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|sw\\.js|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
