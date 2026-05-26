import { describe, expect, it } from "vitest";

import { VAULT_VENDOR_PRESETS } from "./connectors-vault-presets";

describe("connectors-vault-presets Phase 3.6", () => {
  it("covers Phase 3 vendors with unique slugs", () => {
    expect(VAULT_VENDOR_PRESETS.length).toBeGreaterThanOrEqual(10);
    const slugs = VAULT_VENDOR_PRESETS.map((p) => p.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
  });

  it("OAuth presets include HTTPS token endpoints", () => {
    const oauth = VAULT_VENDOR_PRESETS.filter((p) => p.kind === "oauth2");
    expect(oauth.length).toBeGreaterThanOrEqual(3);
    for (const p of oauth) {
      expect(p.tokenEndpoint?.startsWith("https://")).toBe(true);
    }
  });
});
