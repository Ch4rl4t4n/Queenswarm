import { describe, expect, it } from "vitest";

import {
  pickCompactSkillSlugs,
  SKILL_PICKER_PINNED_SLUGS,
} from "@/lib/skill-picker-catalog";
import type { SkillCatalogItem } from "@/lib/skill-picker-catalog";

const catalog: SkillCatalogItem[] = [
  { slug: "context", title: "Context", keywords: [], roles: [], is_builtin: true, is_tenant: false },
  { slug: "decide", title: "Decide", keywords: [], roles: [], is_builtin: true, is_tenant: false },
  { slug: "product-mission", title: "Product Mission", keywords: [], roles: [], is_builtin: true, is_tenant: false },
  { slug: "lead-gen-lane", title: "Lead Gen Lane", keywords: [], roles: [], is_builtin: true, is_tenant: false },
  {
    slug: "seo-blog-factory",
    title: "SEO blog factory",
    keywords: [],
    roles: [],
    is_builtin: false,
    is_tenant: true,
  },
  {
    slug: "newsletter-factory",
    title: "Newsletter factory",
    keywords: [],
    roles: [],
    is_builtin: false,
    is_tenant: true,
  },
];

describe("skill-picker-catalog", () => {
  it("prefers suggested and pinned builtins in compact row", () => {
    const compact = pickCompactSkillSlugs({
      catalog,
      selected: [],
      suggested: ["lead-gen-lane"],
      limit: 4,
    });
    expect(compact[0]).toBe("lead-gen-lane");
    expect(compact).toContain("context");
    expect(compact).not.toContain("seo-blog-factory");
  });

  it("includes tenant skill when explicitly selected", () => {
    const compact = pickCompactSkillSlugs({
      catalog,
      selected: ["seo-blog-factory"],
      suggested: [],
      limit: 6,
    });
    expect(compact).toContain("seo-blog-factory");
  });

  it("pins cover common operator builtins", () => {
    expect(SKILL_PICKER_PINNED_SLUGS).toContain("context");
    expect(SKILL_PICKER_PINNED_SLUGS).toContain("product-mission");
  });
});
