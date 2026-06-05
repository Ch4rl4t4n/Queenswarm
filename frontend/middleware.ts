import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { QS_ACCESS, QS_REFRESH } from "@/lib/auth-cookies";
import { isLikelyValidDashboardAccessToken } from "@/lib/dashboard-access-jwt";
import { hiveOverviewHref } from "@/lib/hive-home-route";
import { appPublicOrigin, isAppDashboardPath, isMarketingHost, marketingPublicOrigin } from "@/lib/marketing-host";

function controlPlaneHome(): string {
  return hiveOverviewHref();
}

/** Paths that bypass auth gates; gated routes rely on HttpOnly ``qs_dashboard_at`` cookie (see ``attachDashboardTokenCookies``). */

const PUBLIC_PREFIXES = [
  "/login",
  "/verify-2fa",
  "/terms",
  "/privacy",
  "/data-deletion",
  "/health",
  "/offline",
  "/magnet",
  "/transparency",
  "/skills",
  "/start",
  "/how-it-works",
  "/verify-first",
];

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

  const host = request.headers.get("host") ?? "";
  const { pathname } = request.nextUrl;
  const marketingHost = isMarketingHost(host);

  if (marketingHost && isAppDashboardPath(pathname)) {
    const target = new URL(pathname, appPublicOrigin());
    target.search = request.nextUrl.search;
    return NextResponse.redirect(target);
  }

  if (marketingHost && (pathname === "/start" || pathname.startsWith("/start/"))) {
    return NextResponse.redirect(new URL("/skills", request.url));
  }

  const marketingPublic =
    pathname === "/skills" ||
    pathname.startsWith("/skills/") ||
    pathname.startsWith("/start") ||
    pathname === "/how-it-works" ||
    pathname === "/verify-first";

  if (!marketingHost && marketingPublic) {
    const target = new URL(pathname, marketingPublicOrigin());
    target.search = request.nextUrl.search;
    return NextResponse.redirect(target);
  }

  if (marketingHost) {
    return NextResponse.next();
  }
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
    if (home !== "/dashboard") {
      return NextResponse.redirect(new URL(home, request.url));
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
