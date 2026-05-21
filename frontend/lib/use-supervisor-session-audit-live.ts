"use client";

import { useEffect } from "react";
import { toast } from "sonner";

import { resolveHiveBearerToken } from "@/lib/hive-bearer-token";
import { buildHiveWebsocketHref } from "@/lib/hive-ws-url";
import type { SupervisorSessionAuditLogRow } from "@/lib/hive-types";

function formatAuditAction(action: string): string {
  return action.replace(/^supervisor_/, "").replaceAll("_", " ");
}

/** Subscribe to live operator audit rows for one supervisor session. */
export function useSupervisorSessionAuditLive(
  sessionId: string,
  onEntry: (entry: SupervisorSessionAuditLogRow) => void,
): void {
  useEffect(() => {
    if (!sessionId) {
      return;
    }

    let alive = true;
    let ws: WebSocket | null = null;

    void (async () => {
      const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? `${window.location.origin}/api/v1`;
      const built = buildHiveWebsocketHref(
        apiBase,
        `agents/sessions/${encodeURIComponent(sessionId)}/audit-live`,
      );
      if (!built || !alive) {
        return;
      }

      const url = new URL(built);
      const token = await resolveHiveBearerToken();
      if (token) {
        url.searchParams.set("token", token);
      }

      ws = new WebSocket(url.toString());
      ws.onmessage = (evt) => {
        if (!alive) {
          return;
        }
        try {
          const data = JSON.parse(evt.data as string) as {
            type?: string;
            entry?: SupervisorSessionAuditLogRow;
          };
          if (data.type !== "supervisor_session.audit" || !data.entry) {
            return;
          }
          onEntry(data.entry);
          toast.message(`Operator audit: ${formatAuditAction(data.entry.action)}`);
        } catch {
          /* ignore malformed frames */
        }
      };
    })();

    return () => {
      alive = false;
      ws?.close();
    };
  }, [sessionId, onEntry]);
}
