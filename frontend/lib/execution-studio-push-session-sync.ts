"use client";

const EXECUTION_STUDIO_PUSH_INTENT_KEY = "qs_execution_studio_push_enabled";

/** Persist operator opt-in so tenant switch can re-register push for the new tenant. */
export function setExecutionStudioPushIntent(enabled: boolean): void {
  if (typeof window === "undefined") {
    return;
  }
  if (enabled) {
    localStorage.setItem(EXECUTION_STUDIO_PUSH_INTENT_KEY, "1");
  } else {
    localStorage.removeItem(EXECUTION_STUDIO_PUSH_INTENT_KEY);
  }
}

/** Return True when operator previously enabled Execution Studio browser push. */
export function executionStudioPushIntentEnabled(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return localStorage.getItem(EXECUTION_STUDIO_PUSH_INTENT_KEY) === "1";
}

/** Best-effort unsubscribe + clear local push intent before logout. */
export async function clearExecutionStudioPushOnLogout(): Promise<void> {
  if (typeof window === "undefined") {
    return;
  }
  setExecutionStudioPushIntent(false);
  try {
    const { unsubscribeExecutionStudioWebPush } = await import("@/lib/execution-studio-web-push");
    await unsubscribeExecutionStudioWebPush();
  } catch {
    /* logout must proceed */
  }
}

/** Re-register push subscription when operator session becomes active (login or tenant switch). */
export async function resyncExecutionStudioPushIfEnabled(): Promise<void> {
  if (typeof window === "undefined" || !executionStudioPushIntentEnabled()) {
    return;
  }
  try {
    const { subscribeExecutionStudioWebPush } = await import("@/lib/execution-studio-web-push");
    await subscribeExecutionStudioWebPush();
  } catch {
    /* session bootstrap must proceed */
  }
}

/** @deprecated Use resyncExecutionStudioPushIfEnabled */
export async function resyncExecutionStudioPushAfterTenantSwitch(): Promise<void> {
  await resyncExecutionStudioPushIfEnabled();
}
