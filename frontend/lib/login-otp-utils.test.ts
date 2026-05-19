import { describe, expect, it } from "vitest";

import { isOtpComplete, normalizeOtpDigit, parseOtpPaste } from "@/lib/login-otp-utils";

describe("login otp utils", () => {
  it("normalizeOtpDigit keeps only the last numeric character", () => {
    expect(normalizeOtpDigit("a9b")).toBe("9");
    expect(normalizeOtpDigit("12")).toBe("2");
  });

  it("parseOtpPaste splits six digits and ignores noise", () => {
    expect(parseOtpPaste("12-34 56")).toEqual(["1", "2", "3", "4", "5", "6"]);
    expect(parseOtpPaste("abc")).toEqual(["", "", "", "", "", ""]);
  });

  it("isOtpComplete requires six filled cells", () => {
    expect(isOtpComplete(["1", "2", "3", "4", "5", "6"])).toBe(true);
    expect(isOtpComplete(["1", "2", "3", "4", "5", ""])).toBe(false);
  });
});
