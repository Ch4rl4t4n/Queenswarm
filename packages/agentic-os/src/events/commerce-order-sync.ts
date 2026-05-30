/** Commerce order sync event — mirrors Redis/swarm_events fan-out from Python backend. */

export type CommerceProvider = "stripe" | "shopify";

export interface CommerceOrderSyncEvent {
  event: "commerce_order_sync";
  provider: CommerceProvider;
  event_id: string;
  event_type: string;
  object_id: string;
  amount_cents?: number | null;
  currency?: string | null;
  order_status?: string | null;
  ingested_at: string;
  firm_id?: string;
}

export function isCommerceOrderSyncEvent(payload: unknown): payload is CommerceOrderSyncEvent {
  if (typeof payload !== "object" || payload === null) return false;
  const p = payload as Record<string, unknown>;
  return p.event === "commerce_order_sync" && typeof p.event_id === "string";
}

/** n8n / Node webhook fan-out handler stub. */
export async function handleCommerceOrderSync(
  event: CommerceOrderSyncEvent,
  handlers: {
    onOrderPaid?: (event: CommerceOrderSyncEvent) => Promise<void>;
    onPaymentFailed?: (event: CommerceOrderSyncEvent) => Promise<void>;
  },
): Promise<void> {
  if (event.event_type === "checkout.session.completed" || event.event_type === "payment_intent.succeeded") {
    await handlers.onOrderPaid?.(event);
    return;
  }
  if (event.event_type === "payment_intent.payment_failed") {
    await handlers.onPaymentFailed?.(event);
  }
}
