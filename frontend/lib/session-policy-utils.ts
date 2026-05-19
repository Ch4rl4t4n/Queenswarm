import type { SessionPolicySnapshot } from "@/lib/session-policy-types";

export function formatAccessTtl(minutes: number): string {
  if (minutes === 1) {
    return "1 minute";
  }
  return `${minutes} minutes`;
}

export function formatRefreshTtl(days: number): string {
  if (days === 1) {
    return "1 day";
  }
  return `${days} days`;
}

export function formatRateLimit(policy: Pick<SessionPolicySnapshot, "rate_limit_requests" | "rate_limit_window_sec">): string {
  const windowSec = Math.max(1, Math.round(policy.rate_limit_window_sec));
  if (windowSec % 60 === 0) {
    const minutes = windowSec / 60;
    return `${policy.rate_limit_requests} req/${minutes === 1 ? "min" : `${minutes} min`} sliding window`;
  }
  return `${policy.rate_limit_requests} req/${windowSec}s sliding window`;
}

export function formatOAuthStateTtl(seconds: number): string {
  const minutes = Math.max(1, Math.round(seconds / 60));
  return `Redis state TTL ${minutes} min`;
}

export function nearestSelectValue(current: number, options: readonly number[]): number {
  return options.reduce((best, candidate) =>
    Math.abs(candidate - current) < Math.abs(best - current) ? candidate : best,
  );
}
