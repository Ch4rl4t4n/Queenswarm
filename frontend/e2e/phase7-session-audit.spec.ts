import { test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";

const sessionId = "44444444-4444-4444-8444-444444444444";
const phase7E2eEnabled = process.env.E2E_PHASE7_SESSION_AUDIT === "1";

function sessionPayload() {
  return [
    {
      id: sessionId,
      goal: "Audit durable session operator trail",
      status: "needs_input",
      runtime_mode: "durable",
      created_by_subject: "dash:test",
      context_summary: { requested_roles: ["researcher"] },
      swarm_id: null,
      task_id: null,
      started_at: new Date().toISOString(),
      completed_at: null,
      error_text: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      sub_agents: [
        {
          id: "55555555-5555-4555-8555-555555555555",
          role: "researcher",
          status: "needs_input",
          runtime_mode: "durable",
          toolset: ["search"],
          short_memory: {},
          spawn_order: 0,
          started_at: new Date().toISOString(),
          completed_at: null,
          last_output: null,
          error_text: null,
        },
      ],
    },
  ];
}

test.describe("Phase 7 session operator audit drawer", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test.beforeEach(() => {
    test.skip(!phase7E2eEnabled, "Set E2E_PHASE7_SESSION_AUDIT=1 to run Phase 7 session audit checks.");
  });

  test.beforeEach(async ({ context, baseURL, page }) => {
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    await page.route("**/api/proxy/agents?limit=120", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.route("**/api/proxy/agents/sessions?limit=40", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(sessionPayload()),
      });
    });

    await page.route("**/api/proxy/agents/sessions/summary", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sessions_total: 1,
          status_counts: { needs_input: 1 },
          running_sessions: 0,
          needs_input_sessions: 1,
          completed_sessions: 0,
          routines_total: 0,
          active_routines: 0,
          due_routines: 0,
        }),
      });
    });

    await page.route(`**/api/proxy/agents/sessions/${sessionId}/events?limit=120`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "evt-1",
            supervisor_session_id: sessionId,
            sub_agent_session_id: null,
            event_type: "session_started",
            level: "info",
            message: "Session started",
            payload: {},
            occurred_at: new Date().toISOString(),
            created_at: new Date().toISOString(),
          },
        ]),
      });
    });

    await page.route(`**/api/proxy/agents/sessions/${sessionId}/shared-context`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session_id: sessionId,
          enabled: false,
          retrieval_contract: "",
          matched_sections: [],
          sections: {},
          pruned_items: 0,
          prompt_block: "",
          context_summary: {},
        }),
      });
    });

    await page.route(`**/api/proxy/agents/sessions/${sessionId}/context-history?limit=8`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            audit_id: "hist-1",
            action: "supervisor_session_control",
            created_at: new Date().toISOString(),
            context_diff: {
              changed: {
                requeued_sub_agents: { before: 0, after: 2 },
              },
            },
            session_status: "running",
            control_action: "resume",
            decision: null,
          },
        ]),
      });
    });

    await page.route(`**/api/proxy/agents/sessions/${sessionId}/audit-logs?limit=12`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "audit-1",
            tenant_id: "66666666-6666-4666-8666-666666666666",
            action: "supervisor_session_create",
            target_type: "supervisor_session",
            target_ref: sessionId,
            actor_user_id: "77777777-7777-4777-8777-777777777777",
            payload: {
              goal_preview: "Audit durable session operator trail",
              runtime_mode: "durable",
            },
            created_at: new Date().toISOString(),
          },
          {
            id: "audit-2",
            tenant_id: "66666666-6666-4666-8666-666666666666",
            action: "supervisor_session_review",
            target_type: "supervisor_session",
            target_ref: sessionId,
            actor_user_id: "77777777-7777-4777-8777-777777777777",
            payload: { decision: "approve" },
            created_at: new Date().toISOString(),
          },
        ]),
      });
    });
  });

  test("session detail drawer shows operator audit trail", async () => {
    test.skip(true, "Session detail drawer removed from agents page.");
  });
});
