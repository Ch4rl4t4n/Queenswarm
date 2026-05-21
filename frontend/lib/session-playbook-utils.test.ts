import { describe, expect, it } from "vitest";

import { defaultPlaybookTopicTags, parsePlaybookTopicTags, playbookRecipeIdFromContext, playbookWasAutoSavedOnReview } from "@/lib/session-playbook-utils";

describe("parsePlaybookTopicTags", () => {
  it("splits comma-separated tags and dedupes", () => {
    expect(parsePlaybookTopicTags("supervisor, playbook, supervisor , pricing")).toEqual([
      "supervisor",
      "playbook",
      "pricing",
    ]);
  });

  it("returns defaults helper tags", () => {
    expect(defaultPlaybookTopicTags()).toContain("operator_playbook");
  });

  it("detects fresh auto-save after approve", () => {
    expect(
      playbookWasAutoSavedOnReview(
        {
          playbook_recipe_id: "abc-123",
          playbook_auto_saved_at: "2026-05-19T10:00:00+00:00",
        },
        null,
      ),
    ).toBe(true);
    expect(
      playbookWasAutoSavedOnReview(
        {
          playbook_recipe_id: "abc-123",
          playbook_auto_saved_at: "2026-05-19T10:00:00+00:00",
        },
        "abc-123",
      ),
    ).toBe(false);
  });

  it("reads playbook recipe id from context summary", () => {
    expect(playbookRecipeIdFromContext({ playbook_recipe_id: "  rid  " })).toBe("rid");
    expect(playbookRecipeIdFromContext({})).toBeNull();
  });
});
