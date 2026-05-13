import { NextResponse } from "next/server";

import { attachDashboardTokenCookies } from "@/lib/auth-token-response";
import {
  hiveRelayNetworkErrorResponse,
  hiveRelayPost,
  hiveRelayReadJson,
  hiveRelayTargetUrl,
} from "@/lib/backend-relay";

interface LoginJson {
  email: string;
  password: string;
}

interface LoginUpstream {
  requires_totp?: boolean;
  requires_2fa?: boolean;
  mfa_required?: boolean;
  pre_auth_token?: string | null;
  mfa_token?: string | null;
  temp_token?: string | null;
  message?: string | null;
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

  const path = "/auth/login";
  const targetUrl = hiveRelayTargetUrl(path);

  let upstream: Response;
  try {
    upstream = await hiveRelayPost(path, { email: body.email, password: body.password });
  } catch (err) {
    return hiveRelayNetworkErrorResponse(err, targetUrl);
  }

  const parsed = await hiveRelayReadJson<LoginUpstream & { detail?: unknown }>(upstream, targetUrl);
  if (!parsed.ok) {
    return parsed.response;
  }
  const payload = parsed.data;

  if (!upstream.ok) {
    return NextResponse.json(
      { detail: typeof payload.detail === "string" ? payload.detail : "Login rejected." },
      { status: upstream.status },
    );
  }

  const requiresOtpStep = Boolean(
    payload.requires_totp || payload.requires_2fa || payload.mfa_required,
  );
  const preRaw =
    (typeof payload.pre_auth_token === "string" ? payload.pre_auth_token : "") ||
    (typeof payload.mfa_token === "string" ? payload.mfa_token : "") ||
    (typeof payload.temp_token === "string" ? payload.temp_token : "");
  const preAuth = preRaw.trim().length ? preRaw.trim() : null;

  if (requiresOtpStep) {
    return NextResponse.json({
      requires_totp: true,
      requires_2fa: true,
      mfa_required: true,
      pre_auth_token: preAuth,
      message: typeof payload.message === "string" ? payload.message : "Enter your 2FA code",
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
}
