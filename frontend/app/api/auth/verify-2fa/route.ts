import { NextResponse } from "next/server";

import { attachDashboardTokenCookies } from "@/lib/auth-token-response";
import { backendHiveUrl } from "@/lib/backend-origin";

interface BodyShape {
  pre_auth_token: string;
  totp_code: string;
}

interface TokenUpstream {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type?: string;
}

export async function POST(request: Request): Promise<NextResponse> {
  let body: BodyShape;
  try {
    body = (await request.json()) as BodyShape;
  } catch {
    return NextResponse.json({ detail: "Invalid JSON payload." }, { status: 400 });
  }

  try {
    const upstream = await fetch(backendHiveUrl("/auth/verify-2fa"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pre_auth_token: body.pre_auth_token, totp_code: body.totp_code }),
      cache: "no-store",
    });

    const payload = (await upstream.json()) as TokenUpstream & { detail?: unknown };

    if (!upstream.ok) {
      return NextResponse.json(
        { detail: typeof payload.detail === "string" ? payload.detail : "Verification failed." },
        { status: upstream.status },
      );
    }

    if (!payload.access_token || !payload.refresh_token) {
      return NextResponse.json({ detail: "Malformed token bundle." }, { status: 502 });
    }

    const res = NextResponse.json({
      ok: true,
      access_token: payload.access_token,
      expires_in: payload.expires_in,
      token_type: payload.token_type ?? "bearer",
    });
    attachDashboardTokenCookies(res, payload);
    return res;
  } catch {
    return NextResponse.json({ detail: "Auth relay unavailable." }, { status: 503 });
  }
}
