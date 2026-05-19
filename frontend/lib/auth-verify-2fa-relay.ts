import { NextResponse } from "next/server";

import { attachDashboardTokenCookies } from "@/lib/auth-token-response";
import { parseVerify2FaBody, type Verify2FaBodyShape } from "@/lib/auth-verify-2fa-utils";
import {
  hiveRelayNetworkErrorResponse,
  hiveRelayPost,
  hiveRelayReadJson,
  hiveRelayTargetUrl,
} from "@/lib/backend-relay";

/** Canonical hive path for TOTP completion (alias of ``/auth/verify-2fa``). */
export const VERIFY_2FA_BACKEND_PATH = "/auth/totp/verify";

export type { Verify2FaBodyShape };

interface TokenUpstream {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type?: string;
}

/** Relay dashboard 2FA verification to the hive backend and attach session cookies. */
export async function relayVerify2Fa(request: Request): Promise<NextResponse> {
  let body: Verify2FaBodyShape;
  try {
    body = (await request.json()) as Verify2FaBodyShape;
  } catch {
    return NextResponse.json({ detail: "Invalid JSON payload." }, { status: 400 });
  }

  const parsed = parseVerify2FaBody(body);
  if (!parsed) {
    return NextResponse.json({ detail: "pre_auth_token and a 6+ digit code are required." }, { status: 400 });
  }

  const targetUrl = hiveRelayTargetUrl(VERIFY_2FA_BACKEND_PATH);

  let upstream: Response;
  try {
    upstream = await hiveRelayPost(VERIFY_2FA_BACKEND_PATH, {
      pre_auth_token: parsed.tokenRaw,
      totp_code: parsed.codeRaw,
    });
  } catch (err) {
    return hiveRelayNetworkErrorResponse(err, targetUrl);
  }

  const relayParsed = await hiveRelayReadJson<TokenUpstream & { detail?: unknown }>(upstream, targetUrl);
  if (!relayParsed.ok) {
    return relayParsed.response;
  }
  const payload = relayParsed.data;

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
