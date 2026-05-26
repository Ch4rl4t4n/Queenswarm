export interface RetryWithBackoffOptions {
  maxAttempts?: number;
  baseDelayMs?: number;
  shouldRetry?: (error: unknown) => boolean;
}

const DEFAULT_SHOULD_RETRY = (error: unknown): boolean => {
  if (error instanceof TypeError) return true;
  if (typeof error === "object" && error !== null && "status" in error) {
    const status = Number((error as { status?: number }).status);
    return status === 502 || status === 503 || status === 504;
  }
  return false;
};

/** Retry async work with exponential backoff (live confirm network blips). */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  options: RetryWithBackoffOptions = {},
): Promise<T> {
  const maxAttempts = options.maxAttempts ?? 3;
  const baseDelayMs = options.baseDelayMs ?? 1_000;
  const shouldRetry = options.shouldRetry ?? DEFAULT_SHOULD_RETRY;

  let lastError: unknown;
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      const isLast = attempt >= maxAttempts - 1;
      if (isLast || !shouldRetry(error)) {
        throw error;
      }
      const delay = baseDelayMs * 2 ** attempt;
      await new Promise((resolve) => window.setTimeout(resolve, delay));
    }
  }
  throw lastError;
}
