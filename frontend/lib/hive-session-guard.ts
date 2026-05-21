/** Client-side auth circuit breaker — stops API storms when refresh/session is dead. */

let sessionDead = false;
let redirectScheduled = false;

/** True after refresh failed or repeated auth rejection — pollers should pause. */
export function isHiveSessionDead(): boolean {
  return sessionDead;
}

/** Mark session unusable and redirect to login once (browser only). */
export function markHiveSessionDead(): void {
  if (sessionDead) {
    return;
  }
  sessionDead = true;
  if (typeof window === "undefined") {
    return;
  }
  if (redirectScheduled) {
    return;
  }
  redirectScheduled = true;
  const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
  window.location.assign(`/login?next=${next}&reason=session_expired`);
}

/** Reset guard after successful login (optional hook from login page). */
export function resetHiveSessionGuard(): void {
  sessionDead = false;
  redirectScheduled = false;
}
