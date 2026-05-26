"use client";

import { useEffect, useState } from "react";

import {
  subscribeSupervisorSessionAuditConnectionState,
  type SupervisorAuditConnectionState,
} from "@/lib/supervisor-session-audit-subscriber";

/** Track audit-live websocket connection state for one supervisor session. */
export function useSupervisorSessionAuditConnectionState(
  sessionId: string,
): SupervisorAuditConnectionState {
  const [state, setState] = useState<SupervisorAuditConnectionState>("idle");

  useEffect(() => {
    if (!sessionId) {
      setState("idle");
      return;
    }
    return subscribeSupervisorSessionAuditConnectionState(sessionId, setState);
  }, [sessionId]);

  return state;
}
