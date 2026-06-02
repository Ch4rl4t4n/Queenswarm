import { describe, expect, it } from "vitest";

import {
  groupMissionKanbanTasks,
  missionKanbanColumnFor,
  shortTaskId,
} from "@/lib/mission-kanban";
import type { TaskRow } from "@/lib/hive-types";

function row(status: string, title = "Test"): TaskRow {
  return {
    id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    title,
    status,
    priority: 5,
    task_type: "agent_run",
  };
}

describe("missionKanbanColumnFor", () => {
  it("maps triage and ready statuses", () => {
    expect(missionKanbanColumnFor("triage")).toBe("triage");
    expect(missionKanbanColumnFor("ready")).toBe("ready");
  });

  it("maps pending to todo and failed to blocked", () => {
    expect(missionKanbanColumnFor("pending")).toBe("todo");
    expect(missionKanbanColumnFor("failed")).toBe("blocked");
  });
});

describe("groupMissionKanbanTasks", () => {
  it("groups tasks into columns", () => {
    const grouped = groupMissionKanbanTasks([
      row("triage", "Big job"),
      row("pending", "Slice 1"),
      row("completed", "Done slice"),
    ]);
    expect(grouped.triage).toHaveLength(1);
    expect(grouped.todo).toHaveLength(1);
    expect(grouped.done).toHaveLength(1);
  });
});

describe("shortTaskId", () => {
  it("formats compact ids", () => {
    expect(shortTaskId("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")).toBe("t_aaaaaaaa");
  });
});
