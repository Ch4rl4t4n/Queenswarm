/** Start the Revenue Swarm Product Mission in Ballroom (session + seven-step chain). */

import { HiveApiError, hivePostJson } from "@/lib/api";
import { stashPendingProductMission } from "@/lib/product-mission-pending";

export interface StartProductMissionOptions {
  /** Optional niche hint (newsletter, crypto alerts, SEO blog…). */
  nicheHint?: string;
}

const DEFAULT_NICHE = "pick the highest-margin niche from hive recipes (newsletter, blog, crypto).";

/**
 * Build operator brief for POST /ballroom/mission.
 */
export function buildProductMissionBrief(nicheHint?: string): string {
  const niche = (nicheHint ?? "").trim() || DEFAULT_NICHE;
  return [
    "Product Mission — Revenue Swarm Factory",
    "",
    "Run the PRODUCT_MISSION workflow end-to-end:",
    "1) Research niche pain, buyer persona, price anchor (€9 / €19 / €29)",
    "2) Decompose deliverable into 3–7 verified swarm workflow steps",
    "3) Simulate every step — block unverified outputs",
    "4) Package SKILL.md bundle + README + Gumroad LISTING.md",
    "5) Publish plan: GitHub folder, Gumroad product, optional Queenswarm Stripe tag",
    "",
    `Niche hint: ${niche}`,
    "Deliver: verified recipe in Recipe Library, ready for Integrations → Skills export.",
  ].join("\n");
}

/**
 * Mint ballroom session, hand off mission to Ballroom page, redirect immediately.
 *
 * Mission LLM chain can run 1–3 minutes — never block the Integrations UI spinner on it.
 */
export async function startProductMission(options: StartProductMissionOptions = {}): Promise<string> {
  const brief = buildProductMissionBrief(options.nicheHint);
  const cap = await hivePostJson<{ session_id?: string }>("ballroom/session", {});
  const sessionId = cap.session_id?.trim();
  if (!sessionId) {
    throw new Error("Ballroom session could not be created.");
  }

  stashPendingProductMission({ session_id: sessionId, user_brief: brief });

  if (typeof window !== "undefined") {
    window.location.assign(`/ballroom?session=${encodeURIComponent(sessionId)}&mission=product`);
  }

  return sessionId;
}

/** Run pending mission once Ballroom session websocket is bound. */
export async function runPendingProductMission(sessionId: string): Promise<void> {
  const { consumePendingProductMission } = await import("@/lib/product-mission-pending");
  const pending = consumePendingProductMission(sessionId);
  if (!pending) {
    return;
  }

  try {
    await hivePostJson("ballroom/mission", {
      user_brief: pending.user_brief,
      session_id: pending.session_id,
    });
  } catch (exc) {
    const msg =
      exc instanceof HiveApiError
        ? exc.message
        : exc instanceof Error
          ? exc.message
          : "Product mission failed to start.";
    throw new Error(msg);
  }
}
