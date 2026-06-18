import { describe, expect, it } from "vitest";

import {
  dedupeResearchProjectUrls,
  normalizeResearchUrl,
  parseResearchProjectUrls,
} from "@/lib/research-project-urls";

describe("research-project-urls", () => {
  it("normalizes host and trailing slash", () => {
    expect(normalizeResearchUrl("https://WWW.Example.com/path/")).toBe("example.com/path");
  });

  it("dedupes www and trailing slash variants", () => {
    const urls = dedupeResearchProjectUrls([
      "https://example.com/report",
      "https://www.example.com/report/",
      "https://other.com/a",
    ]);
    expect(urls).toHaveLength(2);
    expect(urls.some((url) => url.includes("example.com"))).toBe(true);
    expect(urls.some((url) => url.includes("other.com"))).toBe(true);
  });

  it("caps batch at max urls", () => {
    const lines = Array.from({ length: 12 }, (_, i) => `https://example.com/p${i}`);
    expect(parseResearchProjectUrls(lines.join("\n"), 8)).toHaveLength(8);
  });

  it("ignores blank lines", () => {
    expect(parseResearchProjectUrls("\n  \nhttps://a.com\n")).toEqual(["https://a.com"]);
  });
});
