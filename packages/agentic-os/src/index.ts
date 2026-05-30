export type { GateDecision, GateKind, ExecutionMode, RiskTier } from "./gates/gate-decision.js";
export { previewSocialPublishGate } from "./gates/gate-decision.js";

export type { CommerceOrderSyncEvent, CommerceProvider } from "./events/commerce-order-sync.js";
export { isCommerceOrderSyncEvent, handleCommerceOrderSync } from "./events/commerce-order-sync.js";
