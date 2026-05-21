import { NextResponse } from "next/server";

import { QS_ACCESS, QS_REFRESH } from "@/lib/auth-cookies";

interface TokenBundleShape {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

/** Attach HttpOnly JWT cookies expected by the dashboard proxy + SSR fetch helper. */

function refreshCookieMaxAgeSec(): number {
  const daysRaw = process.env.REFRESH_TOKEN_EXPIRE_DAYS ?? process.env.NEXT_PUBLIC_REFRESH_TOKEN_EXPIRE_DAYS ?? "90";
  const days = Number.parseInt(daysRaw, 10);
  const safeDays = Number.isFinite(days) && days > 0 ? days : 90;
  return safeDays * 86_400;
}

export function attachDashboardTokenCookies(res: NextResponse, bundle: TokenBundleShape): void {
  const secure = process.env.NODE_ENV === "production";
  const accessAge = Math.max(120, Number(bundle.expires_in) || 900);
  const refreshAge = refreshCookieMaxAgeSec();
  res.cookies.set(QS_ACCESS, bundle.access_token, {
    httpOnly: true,
    secure,
    sameSite: "lax",
    path: "/",
    maxAge: accessAge,
  });
  res.cookies.set(QS_REFRESH, bundle.refresh_token, {
    httpOnly: true,
    secure,
    sameSite: "lax",
    path: "/",
    maxAge: refreshAge,
  });
}

export function clearDashboardAuthCookies(res: NextResponse): void {
  const secure = process.env.NODE_ENV === "production";
  res.cookies.set(QS_ACCESS, "", { httpOnly: true, secure, sameSite: "lax", path: "/", maxAge: 0 });
  res.cookies.set(QS_REFRESH, "", { httpOnly: true, secure, sameSite: "lax", path: "/", maxAge: 0 });
  /** Legacy mirror cleared for middleware symmetry. */
  res.cookies.set("qs_token", "", { httpOnly: false, secure, sameSite: "lax", path: "/", maxAge: 0 });
}
