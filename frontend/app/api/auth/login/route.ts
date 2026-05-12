import { NextResponse } from "next/server";

import { attachDashboardTokenCookies } from "@/lib/auth-token-response";
import { backendHiveUrl } from "@/lib/backend-origin";

interface LoginJson {
  email: string;
  password: string;
}

interface LoginUpstream {
  requires_totp: boolean;
  pre_auth_token?: string | null;
  tokens?: {
    access_token: string;
    refresh_token: string;
    expires_in: number;
    token_type?: string;
  };
}

export async function POST(request: Request): Promise<NextResponse> {
  let body: LoginJson;
  try {
    body = (await request.json()) as LoginJson;
  } catch {
    return NextResponse.json({ detail: "Invalid JSON payload." }, { status: 400 });
  }

  try {
    const upstream = await fetch(backendHiveUrl("/auth/login"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: body.email, password: body.password }),
      cache: "no-store",
    });

    const payload = (await upstream.json()) as LoginUpstream & { detail?: unknown };

    if (!upstream.ok) {
      return NextResponse.json(
        { detail: typeof payload.detail === "string" ? payload.detail : "Login rejected." },
        { status: upstream.status },
      );
    }

    if (payload.requires_totp) {
      return NextResponse.json({
        requires_totp: true,
        pre_auth_token: payload.pre_auth_token ?? null,
      });
    }

    const bundle = payload.tokens;
    if (!bundle?.access_token || !bundle.refresh_token) {
      return NextResponse.json({ detail: "Malformed auth response." }, { status: 502 });
    }

    const res = NextResponse.json({
      ok: true,
      access_token: bundle.access_token,
      refresh_token: bundle.refresh_token,
      expires_in: bundle.expires_in,
      token_type: bundle.token_type ?? "bearer",
    });
    attachDashboardTokenCookies(res, bundle);
    return res;
  } catch {
    return NextResponse.json({ detail: "Auth relay unavailable." }, { status: 503 });
  }
}
