import { NextResponse } from "next/server";

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
  detail?: unknown;
}

interface TenantSwitchBody {
  tenant_id: string;
}

export async function POST(req: Request): Promise<NextResponse> {
  let body: TenantSwitchBody;
  try {
    body = (await req.json()) as TenantSwitchBody;
  } catch {
    return NextResponse.json({ detail: "Malformed JSON body." }, { status: 400 });
  }
  if (!body.tenant_id || typeof body.tenant_id !== "string") {
    return NextResponse.json({ detail: "tenant_id is required." }, { status: 400 });
  }

  const path = "/auth/tenants/switch";
  const targetUrl = hiveRelayTargetUrl(path);
  let upstream: Response;
  try {
    upstream = await hiveRelayPost(path, { tenant_id: body.tenant_id });
  } catch (err) {
    return hiveRelayNetworkErrorResponse(err, targetUrl);
  }
  const parsed = await hiveRelayReadJson<TokenUpstream>(upstream, targetUrl);
  if (!parsed.ok) {
    return parsed.response;
  }
  const payload = parsed.data;
  if (!upstream.ok) {
    return NextResponse.json(
      { detail: typeof payload.detail === "string" ? payload.detail : "Tenant switch rejected." },
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
