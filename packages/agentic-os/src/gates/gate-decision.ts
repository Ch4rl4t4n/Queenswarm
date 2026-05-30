/** Gate kinds — mirror backend `agentic_gates.GateKind`. */

export type GateKind = "operator_approval" | "real_money" | "social_publish";

export type ExecutionMode = "draft" | "simulate" | "live";

export type RiskTier = "read" | "write" | "publish" | "financial";

export interface GateDecision {
  allowed: boolean;
  gate: GateKind;
  error_code?: string | null;
  message?: string | null;
  risk_tier?: RiskTier | null;
  metadata?: Record<string, unknown>;
}

/** Evaluate social publish gate (client-side preview — server is source of truth). */
export function previewSocialPublishGate(input: {
  mode: ExecutionMode;
  liveEnabled: boolean;
  effectiveConfirmed: boolean;
  confirmReason?: string;
}): GateDecision {
  if (input.mode !== "live") {
    return { allowed: true, gate: "social_publish", metadata: { mode: input.mode } };
  }
  if (!input.liveEnabled) {
    return {
      allowed: false,
      gate: "social_publish",
      error_code: "live_disabled",
      message: "Live social publish disabled.",
    };
  }
  if (!input.effectiveConfirmed) {
    return {
      allowed: false,
      gate: "social_publish",
      error_code: input.confirmReason ?? "approval_required",
      message: "Live publish requires operator confirmation or successful simulate.",
      metadata: { confirm_reason: input.confirmReason },
    };
  }
  return { allowed: true, gate: "social_publish", metadata: { mode: "live" } };
}
