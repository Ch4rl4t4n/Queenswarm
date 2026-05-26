import { describe, expect, it } from "vitest";

import { studioPendingActionHash, studioPendingActionHref } from "@/lib/operator-pending-events";

describe("studioPendingActionHash", () => {
  it("maps browser pending to stable hash", () => {
    expect(studioPendingActionHash({ type: "browser" })).toBe("pending-browser");
  });

  it("maps external pending to connector slug hash", () => {
    expect(
      studioPendingActionHash({
        type: "external",
        connector_slug: "slack_workspace",
        tool_name: "post_message",
      }),
    ).toBe("pending-external-slack_workspace-post_message");
  });

  it("builds deep-link href for notification center", () => {
    expect(studioPendingActionHref({ type: "browser" })).toBe("/integrations?tab=studio#pending-browser");
  });
});
