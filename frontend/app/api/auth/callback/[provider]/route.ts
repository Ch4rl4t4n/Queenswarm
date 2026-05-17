import type { NextRequest } from "next/server";

import { relayOAuthCallback } from "@/lib/oauth-callback-server";

export const runtime = "nodejs";

/** Compatibility shim when redirect URIs include ``/api/auth/callback/:provider`` — behavior matches ``oauth``. */

export async function GET(request: NextRequest): Promise<Response> {
  return relayOAuthCallback(request);
}
