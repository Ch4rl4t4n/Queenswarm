"use client";

import { useEffect, useRef } from "react";
import { toast } from "sonner";

import type { SupervisorSessionAuditLogRow } from "@/lib/hive-types";
import { subscribeSupervisorSessionAudit } from "@/lib/supervisor-session-audit-subscriber";

function formatAuditAction(action: string): string {
  return action.replace(/^supervisor_/, "").replaceAll("_", " ");
}

/** Subscribe to live operator audit rows for one supervisor session. */
export function useSupervisorSessionAuditLive(
  sessionId: string,
  onEntry: (entry: SupervisorSessionAuditLogRow) => void,
  options?: { silent?: boolean },
): void {
  const onEntryRef = useRef(onEntry);
  onEntryRef.current = onEntry;

  useEffect(() => {
    if (!sessionId) {
      return;
    }

    return subscribeSupervisorSessionAudit(sessionId, (entry) => {
      onEntryRef.current(entry);
      if (!options?.silent) {
        toast.message(`Operator audit: ${formatAuditAction(entry.action)}`);
      }
    });
  }, [sessionId, options?.silent]);
}
