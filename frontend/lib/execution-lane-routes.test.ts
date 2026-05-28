import { describe, expect, it } from "vitest";

import {
  AGENTS_HUB_PATH,
  EXECUTION_LANE_CROSS_LINK_LABELS,
  FORAGERS_PATH,
  JOBS_PATH,
  KNOWLEDGE_HIVEMIND_HREF,
  TASKS_HUB_LANE_LINKS,
  TASKS_HUB_PATH,
  WORKFLOWS_PATH,
} from "@/lib/execution-lane-routes";

describe("execution-lane-routes", () => {
  it("exposes stable execution lane paths", () => {
    expect(TASKS_HUB_PATH).toBe("/tasks");
    expect(WORKFLOWS_PATH).toBe("/workflows");
    expect(JOBS_PATH).toBe("/jobs");
    expect(FORAGERS_PATH).toBe("/foragers");
    expect(AGENTS_HUB_PATH).toBe("/agents");
    expect(KNOWLEDGE_HIVEMIND_HREF).toBe("/knowledge#hivemind");
  });

  it("documents tasks hub lane discovery links", () => {
    expect(TASKS_HUB_LANE_LINKS.map((row) => row.href)).toEqual([
      "/tasks/new",
      WORKFLOWS_PATH,
      JOBS_PATH,
      AGENTS_HUB_PATH,
    ]);
  });

  it("uses consistent cross-link labels", () => {
    expect(EXECUTION_LANE_CROSS_LINK_LABELS.toTasksHub).toBe("Tasks hub");
    expect(EXECUTION_LANE_CROSS_LINK_LABELS.toWorkflows).toBe("Workflows");
    expect(EXECUTION_LANE_CROSS_LINK_LABELS.toAsyncJobs).toBe("Jobs");
  });
});
