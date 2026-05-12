import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { QS_ACCESS } from "@/lib/auth-cookies";

const PUBLIC_PREFIXES = ["/login", "/verify-2fa"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const access = request.cookies.get(QS_ACCESS)?.value;

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

  if (!access) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
