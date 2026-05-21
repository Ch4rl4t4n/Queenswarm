/** Lightweight pub/sub so pollers pause when hiveFetch registers a 429 backoff. */

type RateLimitListener = () => void;

const listeners = new Set<RateLimitListener>();

export function subscribeHiveApiRateLimit(listener: RateLimitListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function notifyHiveApiRateLimitChanged(): void {
  for (const listener of listeners) {
    listener();
  }
}
