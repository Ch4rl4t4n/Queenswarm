import { describe, expect, it } from "vitest";

import { isHttpsProbeUrl, normalizeVaultSlug } from "./connectors-vault-utils";

describe("normalizeVaultSlug", () => {
  it("trims_and_lowercases_slug_when_trimmed_input_has_spaces_and_caps", () => {
    expect(normalizeVaultSlug("  Gmail_WORKSPACE  ")).toBe("gmail_workspace");
  });

  it("returns_empty_string_when_input_is_whitespace_only", () => {
    expect(normalizeVaultSlug("   ")).toBe("");
  });
});

describe("isHttpsProbeUrl", () => {
  it("returns_true_for_https_origin_when_parse_succeeds", () => {
    expect(isHttpsProbeUrl("https://api.example.com/v1/me")).toBe(true);
  });

  it("returns_false_for_http_scheme_when_https_required", () => {
    expect(isHttpsProbeUrl("http://api.example.com/")).toBe(false);
  });

  it("returns_false_for_invalid_url_strings", () => {
    expect(isHttpsProbeUrl("not-a-url")).toBe(false);
    expect(isHttpsProbeUrl("")).toBe(false);
  });
});
