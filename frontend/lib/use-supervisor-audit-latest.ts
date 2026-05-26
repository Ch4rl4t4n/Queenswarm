"use client";

import { useCallback, useEffect, useState } from "react";

import type { SupervisorSessionAuditLogRow } from "@/lib/hive-types";
import { useSupervisorSessionAuditLive } from "@/lib/use-supervisor-session-audit-live";

/** Track latest audit row for one supervisor session (HTTP seed + live WS updates). */
export function useSupervisorAuditLatest(
  sessionId: string,
  initial: SupervisorSessionAuditLogRow | null,
): SupervisorSessionAuditLogRow | null {
  const [latest, setLatest] = useState<SupervisorSessionAuditLogRow | null>(initial);

  useEffect(() => {
    setLatest(initial);
  }, [initial, sessionId]);

  const onEntry = useCallback((entry: SupervisorSessionAuditLogRow) => {
    setLatest(entry);
  }, []);

  useSupervisorSessionAuditLive(sessionId, onEntry, { silent: true });

  return latest;
}
