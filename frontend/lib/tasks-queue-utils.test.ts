import { describe, expect, it } from "vitest";

import { deriveTaskCounts } from "@/lib/tasks-queue-utils";

describe("deriveTaskCounts", () => {
  it("classifies running, pending, and completed statuses", () => {
    const counts = deriveTaskCounts([
      { id: "1", title: "A", status: "running", priority: 1, task_type: "action" },
      { id: "2", title: "B", status: "pending", priority: 1, task_type: "eval" },
      { id: "3", title: "C", status: "done", priority: 1, task_type: "sim" },
    ]);

    expect(counts).toEqual({
      active: 2,
      pending: 1,
      completed: 1,
      running: 1,
    });
  });
});

