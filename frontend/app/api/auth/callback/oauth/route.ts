import type { NextRequest } from "next/server";

import { relayOAuthCallback } from "@/lib/oauth-callback-server";

export const runtime = "nodejs";

export async function GET(request: NextRequest): Promise<Response> {
  return relayOAuthCallback(request);
}
