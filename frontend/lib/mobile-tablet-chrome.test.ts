import { describe, expect, it } from "vitest";

import { mobileChromeTitleForPath } from "@/lib/mobile-tablet-chrome";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "@/lib/feature-flags";

describe("mobileChromeTitleForPath", () => {
  it("returns zone titles for canonical routes", () => {
    expect(mobileChromeTitleForPath("/swarms")).toEqual({ kicker: "Swarms", title: "Swarms" });
    expect(mobileChromeTitleForPath("/integrations")).toEqual({ kicker: "Integrations", title: "Integrations" });
    expect(mobileChromeTitleForPath("/settings/llm-keys")).toEqual({
      kicker: "Settings",
      title: "LLM & Voice",
    });
  });

  it("returns Agentic OS for operator home when CP enabled", () => {
    if (!OPERATOR_CONTROL_PLANE_ENABLED) {
      return;
    }
    expect(mobileChromeTitleForPath("/agentic-os")).toEqual({
      kicker: "Agentic OS",
      title: "Agentic OS",
    });
  });
});
