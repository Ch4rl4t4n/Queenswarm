"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { hiveGet, hivePostJson } from "@/lib/api";

export interface MissionFeedEvent {
  id: string;
  kind: string;
  title: string;
  body: string;
  href: string;
  entity_id?: string | null;
  created_at?: string;
  read?: boolean;
}

const POLL_MS = 25_000;

export function useOperatorMissionFeed(enabled = true): {
  events: MissionFeedEvent[];
  unread: number;
  busy: boolean;
  dismiss: (eventIds: string[]) => Promise<void>;
  refresh: () => Promise<void>;
} {
  const [events, setEvents] = useState<MissionFeedEvent[]>([]);
  const [unread, setUnread] = useState(0);
  const [busy, setBusy] = useState(false);
  const toastedRef = useRef<Set<string>>(new Set());

  const refresh = useCallback(async () => {
    if (!enabled) {
      return;
    }
    setBusy(true);
    try {
      const data = await hiveGet<{ events: MissionFeedEvent[]; unread: number }>(
        "solo-operator/mission-feed?limit=15",
      );
      setEvents(data.events ?? []);
      setUnread(data.unread ?? 0);
      for (const ev of data.events ?? []) {
        if (ev.read || toastedRef.current.has(ev.id)) {
          continue;
        }
        toastedRef.current.add(ev.id);
        toast.success(ev.title, {
          description: ev.body.length > 120 ? `${ev.body.slice(0, 117)}…` : ev.body,
        });
      }
    } catch {
      /* offline */
    } finally {
      setBusy(false);
    }
  }, [enabled]);

  const dismiss = useCallback(
    async (eventIds: string[]) => {
      if (!eventIds.length) {
        return;
      }
      try {
        await hivePostJson("solo-operator/mission-feed/dismiss", { event_ids: eventIds });
        await refresh();
      } catch {
        /* ignore */
      }
    },
    [refresh],
  );

  useEffect(() => {
    if (!enabled) {
      return;
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [enabled, refresh]);

  return { events, unread, busy, dismiss, refresh };
}
