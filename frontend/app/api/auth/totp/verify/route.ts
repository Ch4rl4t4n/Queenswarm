import { NextResponse } from "next/server";

import { attachDashboardTokenCookies } from "@/lib/auth-token-response";
import {
  hiveRelayNetworkErrorResponse,
  hiveRelayPost,
  hiveRelayReadJson,
  hiveRelayTargetUrl,
} from "@/lib/backend-relay";

interface BodyShape {
  email?: string;
  code?: string;
  totp_code?: string;
  pre_auth_token?: string;
  mfa_token?: string;
  temp_token?: string;
}

interface TokenUpstream {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type?: string;
}

/** Completes dashboard login — forwards to hive ``/auth/totp/verify`` (alias of verify-2fa). */
export async function POST(request: Request): Promise<NextResponse> {
  let body: BodyShape;
  try {
    body = (await request.json()) as BodyShape;
  } catch {
    return NextResponse.json({ detail: "Invalid JSON payload." }, { status: 400 });
  }

  const codeRaw =
    (typeof body.totp_code === "string" && body.totp_code.trim() ? body.totp_code.trim() : "") ||
    (typeof body.code === "string" && body.code.trim() ? body.code.trim() : "");
  const tokenRaw =
    (typeof body.pre_auth_token === "string" ? body.pre_auth_token.trim() : "") ||
    (typeof body.mfa_token === "string" ? body.mfa_token.trim() : "") ||
    (typeof body.temp_token === "string" ? body.temp_token.trim() : "");


  if (!tokenRaw || !codeRaw || codeRaw.length < 6) {
    return NextResponse.json({ detail: "pre_auth_token and a 6+ digit code are required." }, { status: 400 });
  }



  const path = "/auth/totp/verify";
  const targetUrl = hiveRelayTargetUrl(path);

  let upstream: Response;
  try {
    upstream = await hiveRelayPost(path, {
      pre_auth_token: tokenRaw,
      totp_code: codeRaw,
    });
  } catch (err) {
    return hiveRelayNetworkErrorResponse(err, targetUrl);
  }

  const parsed = await hiveRelayReadJson<TokenUpstream & { detail?: unknown }>(upstream, targetUrl);
  if (!parsed.ok) {
    return parsed.response;
  }
  const payload = parsed.data;

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
}
