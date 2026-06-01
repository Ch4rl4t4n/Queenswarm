import { describe, expect, it } from "vitest";

import { MANUAL_HREFS } from "@/lib/manual-routes";

describe("MANUAL_HREFS", () => {
  it("maps canonical workflow destinations to in-app paths", () => {
    expect(MANUAL_HREFS.agentsSessions).toBe("/agents#sessions");
    expect(MANUAL_HREFS.knowledgeCurated).toBe("/knowledge#memory");
    expect(MANUAL_HREFS.settingsSecurity).toBe("/settings/security");
  });
});
