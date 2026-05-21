/** Pending Product Mission handoff Integrations → Ballroom (sessionStorage). */

export const PRODUCT_MISSION_PENDING_KEY = "qs_product_mission_pending";

export interface PendingProductMission {
  session_id: string;
  user_brief: string;
}

export function stashPendingProductMission(payload: PendingProductMission): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(PRODUCT_MISSION_PENDING_KEY, JSON.stringify(payload));
}

export function consumePendingProductMission(sessionId: string): PendingProductMission | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.sessionStorage.getItem(PRODUCT_MISSION_PENDING_KEY);
  if (!raw) {
    return null;
  }
  window.sessionStorage.removeItem(PRODUCT_MISSION_PENDING_KEY);
  try {
    const parsed = JSON.parse(raw) as PendingProductMission;
    if (parsed.session_id?.trim() !== sessionId.trim()) {
      return null;
    }
    if (!parsed.user_brief?.trim()) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}
