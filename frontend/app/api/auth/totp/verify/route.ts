import { relayVerify2Fa } from "@/lib/auth-verify-2fa-relay";

/** Completes dashboard login — forwards to hive ``/auth/totp/verify``. */
export async function POST(request: Request): Promise<Response> {
  return relayVerify2Fa(request);
}
