/** Session-scoped stale-while-revalidate cache for Cockpit core snapshot. */

const CACHE_KEY = "qs_cockpit_core_v1";
const MAX_AGE_MS = 120_000;

interface CockpitCacheEnvelope<T> {
  at: number;
  snapshot: T;
}

export function readCockpitCoreCache<T>(): T | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as CockpitCacheEnvelope<T>;
    if (Date.now() - parsed.at > MAX_AGE_MS) {
      sessionStorage.removeItem(CACHE_KEY);
      return null;
    }
    return parsed.snapshot;
  } catch {
    return null;
  }
}

export function writeCockpitCoreCache<T>(snapshot: T): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    const envelope: CockpitCacheEnvelope<T> = { at: Date.now(), snapshot };
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(envelope));
  } catch {
    /* quota / private mode — ignore */
  }
}

/** Warm core snapshot on sidebar hover (best-effort). */
let prefetchInFlight: Promise<void> | null = null;

export function prefetchCockpitCoreSnapshot(): void {
  if (typeof window === "undefined" || prefetchInFlight) {
    return;
  }
  const cached = readCockpitCoreCache<unknown>();
  if (cached) {
    return;
  }
  prefetchInFlight = import("@/lib/api")
    .then(({ hiveGet }) => hiveGet<unknown>("operator/cockpit?scope=core"))
    .then((snapshot) => {
      writeCockpitCoreCache(snapshot);
    })
    .catch(() => {
      /* best-effort */
    })
    .finally(() => {
      prefetchInFlight = null;
    });
}
