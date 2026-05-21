import { describe, expect, it } from "vitest";

import { flattenContextDiffLines } from "./supervisor-context-diff";

describe("flattenContextDiffLines", () => {
  it("flattens nested autonomy_state changes", () => {
    const lines = flattenContextDiffLines({
      nested: {
        autonomy_state: {
          changed: {
            level: { before: 1, after: 2 },
          },
        },
      },
    });
    expect(lines.some((line) => line.key === "autonomy_state.level" && line.text === "1 → 2")).toBe(true);
  });

  it("flattens journal append mutations", () => {
    const lines = flattenContextDiffLines({
      nested: {
        reflection_journal: {
          added_items: [{ step: 2 }],
          before_len: 1,
          after_len: 2,
        },
      },
    });
    expect(lines.some((line) => line.key === "reflection_journal.[append]")).toBe(true);
  });
});
