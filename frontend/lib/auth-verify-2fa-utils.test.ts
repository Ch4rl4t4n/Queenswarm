import { describe, expect, it } from "vitest";

import { parseVerify2FaBody } from "@/lib/auth-verify-2fa-utils";

describe("parseVerify2FaBody", () => {
  it("accepts pre_auth_token and totp_code when both present", () => {
    const parsed = parseVerify2FaBody({
      pre_auth_token: " pre-token ",
      totp_code: "123456",
    });
    expect(parsed).toEqual({ tokenRaw: "pre-token", codeRaw: "123456" });
  });

  it("falls back to mfa_token and code aliases", () => {
    const parsed = parseVerify2FaBody({
      mfa_token: "mfa",
      code: "654321",
    });
    expect(parsed).toEqual({ tokenRaw: "mfa", codeRaw: "654321" });
  });

  it("returns null when code shorter than six digits", () => {
    expect(parseVerify2FaBody({ pre_auth_token: "x", totp_code: "12345" })).toBeNull();
  });

  it("returns null when token missing", () => {
    expect(parseVerify2FaBody({ totp_code: "123456" })).toBeNull();
  });
});
