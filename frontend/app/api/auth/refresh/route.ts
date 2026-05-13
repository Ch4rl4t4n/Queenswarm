import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { QS_REFRESH } from "@/lib/auth-cookies";
import { attachDashboardTokenCookies } from "@/lib/auth-token-response";
import {
  hiveRelayNetworkErrorResponse,
  hiveRelayPost,
  hiveRelayReadJson,
  hiveRelayTargetUrl,
} from "@/lib/backend-relay";

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

  const path = "/auth/refresh";
  const targetUrl = hiveRelayTargetUrl(path);

  let upstream: Response;
  try {
    upstream = await hiveRelayPost(path, { refresh_token: refresh });
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
}
