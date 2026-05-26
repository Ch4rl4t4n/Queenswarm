import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { QS_ACCESS } from "@/lib/auth-cookies";
import { isLikelyValidDashboardAccessToken } from "@/lib/dashboard-access-jwt";

/** Exposes the short-lived bearer for browser WebSocket subscriptions (same-origin only). */

export async function GET(): Promise<NextResponse> {
  const jar = await cookies();
  const access = jar.get(QS_ACCESS)?.value?.trim() ?? "";
  if (!access || !isLikelyValidDashboardAccessToken(access)) {
    return NextResponse.json({ token: null }, { status: 401 });
  }
  return NextResponse.json({ token: access });
}
