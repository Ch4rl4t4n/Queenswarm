import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { QS_REFRESH } from "@/lib/auth-cookies";
import { clearDashboardAuthCookies } from "@/lib/auth-token-response";
import { backendHiveUrl } from "@/lib/backend-origin";

export async function POST(): Promise<NextResponse> {
  const jar = await cookies();
  const refresh = jar.get(QS_REFRESH)?.value;
  const res = NextResponse.json({ ok: true });

  if (refresh) {
    try {
      await fetch(backendHiveUrl("/auth/logout"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
        cache: "no-store",
      });
    } catch {
      /* best-effort revoke */
    }
  }

  clearDashboardAuthCookies(res);
  return res;
}
