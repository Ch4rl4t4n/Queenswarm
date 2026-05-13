import { NextResponse } from "next/server";

import { attachDashboardTokenCookies } from "@/lib/auth-token-response";
import {
  hiveRelayNetworkErrorResponse,
  hiveRelayPost,
  hiveRelayReadJson,
  hiveRelayTargetUrl,
} from "@/lib/backend-relay";

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

  const path = "/auth/verify-2fa";
  const targetUrl = hiveRelayTargetUrl(path);

  let upstream: Response;
  try {
    upstream = await hiveRelayPost(path, {
      pre_auth_token: body.pre_auth_token,
      totp_code: body.totp_code,
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
