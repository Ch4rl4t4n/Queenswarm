import { relayVerify2Fa } from "@/lib/auth-verify-2fa-relay";

/** Backward-compatible alias — same handler as ``/api/auth/totp/verify``. */
export async function POST(request: Request): Promise<Response> {
  return relayVerify2Fa(request);
}
