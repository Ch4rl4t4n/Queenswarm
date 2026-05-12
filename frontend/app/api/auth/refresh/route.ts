import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { QS_REFRESH } from "@/lib/auth-cookies";
import { attachDashboardTokenCookies } from "@/lib/auth-token-response";
import { backendHiveUrl } from "@/lib/backend-origin";

interface TokenUpstream {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type?: string;
}

export async function POST(): Promise<NextResponse> {
  const jar = await cookies();
  const refresh = jar.get(QS_REFRESH)?.value;
  if (!refresh) {
    return NextResponse.json({ detail: "Missing refresh session." }, { status: 401 });
  }

  try {
    const upstream = await fetch(backendHiveUrl("/auth/refresh"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
      cache: "no-store",
    });

    const payload = (await upstream.json()) as TokenUpstream & { detail?: unknown };

    if (!upstream.ok) {
      return NextResponse.json(
        { detail: typeof payload.detail === "string" ? payload.detail : "Refresh rejected." },
        { status: upstream.status },
      );
    }

    if (!payload.access_token || !payload.refresh_token) {
      return NextResponse.json({ detail: "Malformed token bundle." }, { status: 502 });
    }

    const res = NextResponse.json({ ok: true });
    attachDashboardTokenCookies(res, payload);
    return res;
  } catch {
    return NextResponse.json({ detail: "Auth relay unavailable." }, { status: 503 });
  }
}
