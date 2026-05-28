import { describe, expect, it } from "vitest";

import { LIVE_PLATFORM_CAPABILITIES } from "@/lib/platform-capabilities-catalog";
import {
  buildCapabilitiesMarkdown,
  buildCapabilitiesPlainText,
  buildCapabilitiesPrintHtml,
  buildSingleCapabilityMarkdown,
} from "@/lib/platform-capabilities-export";

describe("platform-capabilities-export", () => {
  it("markdown includes architecture live and planned sections", () => {
    const md = buildCapabilitiesMarkdown();
    expect(md).toContain("# Queenswarm — Platform Capabilities Atlas");
    expect(md).toContain("## Architektúra");
    expect(md).toContain("## Live features");
    expect(md).toContain("## Plánované features (roadmap)");
    expect(md).toContain("Dynamic Supervisor Sessions");
    expect(md).toContain("Pro tier feature gates");
  });

  it("plain text strips markdown markers", () => {
    const text = buildCapabilitiesPlainText();
    expect(text).not.toContain("**");
    expect(text).toContain("Queenswarm — Platform Capabilities Atlas");
  });

  it("print html is valid document with title", () => {
    const html = buildCapabilitiesPrintHtml();
    expect(html).toContain("<!DOCTYPE html>");
    expect(html).toContain("Queenswarm Capabilities Atlas");
  });

  it("single capability export includes competitive edge", () => {
    const cap = LIVE_PLATFORM_CAPABILITIES[0];
    expect(buildSingleCapabilityMarkdown(cap)).toContain("Oproti konkurencii");
  });
});
