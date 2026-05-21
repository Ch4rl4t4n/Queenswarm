import { describe, expect, it } from "vitest";

import { knowledgeTabFromHash, knowledgeTabHref } from "@/lib/knowledge-routes";

describe("knowledgeTabHref", () => {
  it("returns bare path for default hivemind tab", () => {
    expect(knowledgeTabHref("hivemind")).toBe("/knowledge");
  });

  it("returns hash path for non-default tabs", () => {
    expect(knowledgeTabHref("outputs")).toBe("/knowledge#outputs");
    expect(knowledgeTabHref("recipes")).toBe("/knowledge#recipes");
  });
});

describe("knowledgeTabFromHash", () => {
  it("maps canonical and legacy hash aliases", () => {
    expect(knowledgeTabFromHash("#hivemind")).toBe("hivemind");
    expect(knowledgeTabFromHash("#outputs")).toBe("outputs");
    expect(knowledgeTabFromHash("#archive")).toBe("outputs");
    expect(knowledgeTabFromHash("#recipes")).toBe("recipes");
    expect(knowledgeTabFromHash("#learning")).toBe("recipes");
    expect(knowledgeTabFromHash("#dreaming")).toBe("dreaming");
  });

  it("returns null for empty or unknown hashes", () => {
    expect(knowledgeTabFromHash("")).toBeNull();
    expect(knowledgeTabFromHash("#")).toBeNull();
    expect(knowledgeTabFromHash("#unknown")).toBeNull();
  });
});
