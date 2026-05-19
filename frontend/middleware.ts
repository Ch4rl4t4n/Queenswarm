import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { QS_ACCESS } from "@/lib/auth-cookies";

/** Paths that bypass auth gates; gated routes rely on HttpOnly ``qs_dashboard_at`` cookie (see ``attachDashboardTokenCookies``). */

const PUBLIC_PREFIXES = ["/login", "/verify-2fa", "/terms", "/privacy", "/health", "/offline"];

/** PWA shell assets — no auth redirect (mobile/tablet install + offline fallback). */
const PUBLIC_EXACT = new Set([
  "/manifest.webmanifest",
  "/manifest",
  "/sw.js",
  "/icon",
  "/apple-icon",
]);

function base64UrlDecode(input: string): string | null {
  const normalized = input.replace(/-/g, "+").replace(/_/g, "/");
  const padding = normalized.length % 4;
  const padded = padding ? normalized.padEnd(normalized.length + (4 - padding), "=") : normalized;
  try {
    return atob(padded);
  } catch {
    return null;
  }
}

function isLikelyValidDashboardJwt(raw: string): boolean {
  const trimmed = raw.trim();
  if (!trimmed) {
    return false;
  }
  const parts = trimmed.split(".");
  if (parts.length < 2) {
    return false;
  }
  const payloadRaw = base64UrlDecode(parts[1] ?? "");
  if (!payloadRaw) {
    return false;
  }
  try {
    const payload = JSON.parse(payloadRaw) as { exp?: unknown; sub?: unknown };
    if (typeof payload.exp !== "number") {
      return false;
    }
    if (payload.exp <= Math.floor(Date.now() / 1000)) {
      return false;
    }
    return typeof payload.sub === "string" && payload.sub.trim().length > 0;
  } catch {
    return false;
  }
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

  if (access && (pathname.startsWith("/login") || pathname.startsWith("/verify-2fa"))) {
    return NextResponse.redirect(new URL("/", request.url));
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
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", buildNextTarget(request.nextUrl));
    const response = NextResponse.redirect(url);
    response.cookies.delete(QS_ACCESS);
    response.cookies.delete("qs_token");
    response.cookies.delete("qs_dashboard_rt");
    return response;
  }

  if (!access) {
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
