/** Pure helpers for six-digit login OTP inputs. */

export function normalizeOtpDigit(value: string): string {
  return value.replace(/\D/g, "").slice(-1);
}

export function parseOtpPaste(text: string): string[] {
  const clean = text.replace(/\D/g, "").slice(0, 6);
  return Array.from({ length: 6 }, (_, index) => clean[index] ?? "");
}

export function isOtpComplete(digits: readonly string[]): boolean {
  return digits.length === 6 && digits.every((digit) => digit !== "");
}
