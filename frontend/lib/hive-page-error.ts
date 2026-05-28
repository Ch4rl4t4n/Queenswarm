/** Inline error/notice surface for {@link HivePageShell} (Phase 8.2 / v2.1). */

export type HivePageShellAlertTone = "error" | "warn";

export interface HivePageShellErrorOptions {
  tone?: HivePageShellAlertTone;
  onDismiss?: () => void;
  onRetry?: () => void;
  retryBusy?: boolean;
  testId?: string;
}

export interface HivePageShellErrorProps {
  message: string;
  tone?: HivePageShellAlertTone;
  onDismiss?: () => void;
  onRetry?: () => void;
  retryBusy?: boolean;
  testId?: string;
}

function resolveOptions(onDismissOrOptions?: (() => void) | HivePageShellErrorOptions): HivePageShellErrorOptions {
  if (typeof onDismissOrOptions === "function") {
    return { onDismiss: onDismissOrOptions };
  }
  return onDismissOrOptions ?? {};
}

/** Map nullable client fetch errors to HivePageShell `error` prop. */
export function hivePageShellError(
  message: string | null | undefined,
  onDismissOrOptions?: (() => void) | HivePageShellErrorOptions,
): HivePageShellErrorProps | null {
  const trimmed = message?.trim();
  if (!trimmed) {
    return null;
  }
  const options = resolveOptions(onDismissOrOptions);
  return {
    message: trimmed,
    tone: options.tone ?? "error",
    onDismiss: options.onDismiss,
    onRetry: options.onRetry,
    retryBusy: options.retryBusy,
    testId: options.testId,
  };
}

/** Non-blocking warn/sync notice (e.g. Agents ledger poll pending). */
export function hivePageShellNotice(
  message: string | null | undefined,
  options?: HivePageShellErrorOptions,
): HivePageShellErrorProps | null {
  return hivePageShellError(message, { ...options, tone: "warn" });
}

/** Prefer the first non-empty message (e.g. roster + swarm load errors). */
export function hivePageShellErrorFirst(
  messages: Array<string | null | undefined>,
  onDismissOrOptions?: (() => void) | HivePageShellErrorOptions,
): HivePageShellErrorProps | null {
  for (const message of messages) {
    const mapped = hivePageShellError(message, onDismissOrOptions);
    if (mapped) {
      return mapped;
    }
  }
  return null;
}

/** Agents control plane — error first, then SSR pending warn with shared retry surface. */
export function hivePageShellAgentsSync(input: {
  rosterError: string | null;
  swarmsError: string | null;
  rosterSyncPending?: boolean;
  onRetry?: () => void;
  retryBusy?: boolean;
}): HivePageShellErrorProps | null {
  const retryOptions: HivePageShellErrorOptions = {
    onRetry: input.onRetry,
    retryBusy: input.retryBusy,
    testId: "agents-sync-banner",
  };

  const fetchError = hivePageShellErrorFirst([input.rosterError, input.swarmsError], retryOptions);
  if (fetchError) {
    return fetchError;
  }

  if (input.rosterSyncPending) {
    return hivePageShellNotice("Agent ledger syncing — live poll will retry shortly.", retryOptions);
  }

  return null;
}
