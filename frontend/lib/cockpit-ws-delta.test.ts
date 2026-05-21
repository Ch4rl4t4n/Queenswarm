import { describe, expect, it } from "vitest";

import type { DashboardCockpitBundle } from "@/lib/cockpit-bundle";
import { applyCockpitWsDelta, applyTaskQueueWsDelta, shouldRevalidateCockpitAfterPulse } from "@/lib/cockpit-ws-delta";
import type { AgentRow, TaskQueueResponse } from "@/lib/hive-types";

function sampleBundle(agents: AgentRow[]): DashboardCockpitBundle {
  return {
    generated_at: "2026-05-21T12:00:00.000Z",
    revision: 100,
    agents,
    recent_tasks: [],
    summary: {
      generated_at: "2026-05-21T12:00:00.000Z",
      agents: {
        total: agents.length,
        by_status: { idle: agents.length },
        by_hive_tier: { worker: agents.length },
      },
      tasks: { pending: 2 },
    },
    system_status: {
      agents_total: agents.length,
      agents_running: 0,
      tasks_running: 1,
      tasks_pending: 2,
      llm_grok: true,
      llm_anthropic: false,
    },
  };
}

describe("applyCockpitWsDelta", () => {
  it("patches agent status and summary counts without refetch", () => {
    const agent: AgentRow = {
      id: "bee-1",
      name: "Scout",
      role: "scraper",
      status: "idle",
      swarm_id: null,
      pollen_points: 10,
      performance_score: 0.4,
      hive_tier: "worker",
    };
    const bundle = sampleBundle([agent]);
    const next = applyCockpitWsDelta(bundle, {
      type: "hive.snapshot",
      revision: 101,
      system_status: {
        agents_total: 1,
        agents_running: 1,
        tasks_running: 1,
        tasks_pending: 3,
        llm_grok: true,
        llm_anthropic: false,
      },
      agent_deltas: [
        {
          id: "bee-1",
          status: "running",
          pollen_points: 12,
          performance_score: 0.55,
          current_task_title: "Scrape docs",
        },
      ],
    });

    expect(next.revision).toBe(101);
    expect(next.agents[0]?.status).toBe("running");
    expect(next.agents[0]?.pollen_points).toBe(12);
    expect(next.summary.tasks.pending).toBe(3);
    expect(next.summary.agents.by_status.running).toBe(1);
    expect(next.summary.agents.by_status.idle).toBeUndefined();
  });

  it("replaces recent_tasks strip from pulse", () => {
    const bundle = sampleBundle([]);
    const next = applyCockpitWsDelta(bundle, {
      type: "hive.snapshot",
      revision: 110,
      system_status: bundle.system_status,
      recent_tasks: [
        {
          id: "task-1",
          title: "Scrape sitemap",
          status: "running",
          priority: 1,
          task_type: "scrape",
        },
      ],
    });
    expect(next.recent_tasks).toHaveLength(1);
    expect(next.recent_tasks[0]?.title).toBe("Scrape sitemap");
  });
});

describe("applyTaskQueueWsDelta", () => {
  it("merges strip rows and updates counts", () => {
    const current: TaskQueueResponse = {
      generated_at: "2026-05-21T12:00:00.000Z",
      running_count: 1,
      pending_count: 2,
      completed_today_count: 0,
      tasks: [
        {
          id: "task-old",
          short_id: "t-old1",
          title: "Old task",
          status: "pending",
          task_type: "scrape",
          swarm_label: "Scout Swarm",
          lane: "scout",
          steps_done: 0,
          steps_total: 3,
          progress_pct: 0,
          updated_at: "2026-05-21T11:00:00.000Z",
          seconds_ago: 3600,
        },
      ],
    };
    const next = applyTaskQueueWsDelta(current, {
      generated_at: "2026-05-21T12:05:00.000Z",
      running_count: 2,
      pending_count: 1,
      completed_today_count: 3,
      tasks: [
        {
          id: "task-new",
          short_id: "t-new1",
          title: "New task",
          status: "running",
          task_type: "evaluate",
          swarm_label: "Eval Swarm",
          lane: "eval",
          steps_done: 1,
          steps_total: 4,
          progress_pct: 25,
          updated_at: "2026-05-21T12:05:00.000Z",
          seconds_ago: 5,
        },
      ],
    });
    expect(next.running_count).toBe(2);
    expect(next.tasks[0]?.id).toBe("task-new");
    expect(next.tasks.some((row) => row.id === "task-old")).toBe(true);
  });
});

describe("shouldRevalidateCockpitAfterPulse", () => {
  it("requires refetch when roster total changes", () => {
    const bundle = sampleBundle([]);
    expect(
      shouldRevalidateCockpitAfterPulse(bundle, {
        type: "hive.snapshot",
        revision: 102,
        agents: 5,
        system_status: {
          agents_total: 5,
          agents_running: 0,
          tasks_running: 0,
          tasks_pending: 0,
          llm_grok: false,
          llm_anthropic: false,
        },
      }),
    ).toBe(true);
  });

  it("allows delta patch for known agents", () => {
    const agent: AgentRow = {
      id: "bee-1",
      name: "Scout",
      role: "scraper",
      status: "idle",
      swarm_id: null,
      pollen_points: 0,
      performance_score: 0,
    };
    const bundle = sampleBundle([agent]);
    expect(
      shouldRevalidateCockpitAfterPulse(bundle, {
        type: "hive.snapshot",
        revision: 103,
        system_status: bundle.system_status,
        agent_deltas: [{ id: "bee-1", status: "running", pollen_points: 1, performance_score: 0.2 }],
      }),
    ).toBe(false);
  });
});
