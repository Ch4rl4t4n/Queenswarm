export interface Verify2FaBodyShape {
  email?: string;
  code?: string;
  totp_code?: string;
  pre_auth_token?: string;
  mfa_token?: string;
  temp_token?: string;
}

export function parseVerify2FaBody(body: Verify2FaBodyShape): { tokenRaw: string; codeRaw: string } | null {
  const codeRaw =
    (typeof body.totp_code === "string" && body.totp_code.trim() ? body.totp_code.trim() : "") ||
    (typeof body.code === "string" && body.code.trim() ? body.code.trim() : "");
  const tokenRaw =
    (typeof body.pre_auth_token === "string" ? body.pre_auth_token.trim() : "") ||
    (typeof body.mfa_token === "string" ? body.mfa_token.trim() : "") ||
    (typeof body.temp_token === "string" ? body.temp_token.trim() : "");

  if (!tokenRaw || !codeRaw || codeRaw.length < 6) {
    return null;
  }
  return { tokenRaw, codeRaw };
}
