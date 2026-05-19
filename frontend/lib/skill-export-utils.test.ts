import { describe, expect, it } from "vitest";

import { hiveMdFromBundle, skillMdFromBundle } from "@/lib/skill-export-utils";
import type { SkillExportResponse } from "@/lib/hive-types";

const SAMPLE_BUNDLE: SkillExportResponse = {
  meta: {
    source: "queenswarm.love",
    recipe_id: "00000000-0000-4000-8000-000000000001",
    recipe_name: "Sample",
    slug: "sample",
    verified: true,
    success_rate: 0.8,
    avg_pollen_earned: 10,
    success_count: 4,
    fail_count: 1,
    topic_tags: ["test"],
    export_version: "1.0.0",
  },
  files: [
    { path: "sample/SKILL.md", content: "# Sample Skill" },
    { path: "sample/HIVE.md", content: "# HIVE" },
  ],
  install_command: "npx skills@latest add queenswarm/sample",
  install_hint: "hint",
};

describe("skillMdFromBundle", () => {
  it("returns SKILL.md file when present", () => {
    const file = skillMdFromBundle(SAMPLE_BUNDLE);
    expect(file?.path).toBe("sample/SKILL.md");
    expect(file?.content).toContain("Sample Skill");
  });
});

describe("hiveMdFromBundle", () => {
  it("returns HIVE.md file when present", () => {
    const file = hiveMdFromBundle(SAMPLE_BUNDLE);
    expect(file?.path).toBe("sample/HIVE.md");
  });
});
