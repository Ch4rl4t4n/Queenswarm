"use client";

import { createContext, useContext, type ReactNode } from "react";

import {
  useOperatorMissionFeed,
  type MissionFeedEvent,
} from "@/lib/hooks/use-operator-mission-feed";
import { useMissionSearchAutoBackfill } from "@/lib/hooks/use-mission-search-auto-backfill";

export interface OperatorMissionFeedContextValue {
  events: MissionFeedEvent[];
  unread: number;
  busy: boolean;
  dismiss: (eventIds: string[]) => Promise<void>;
  refresh: () => Promise<void>;
}

const EMPTY: OperatorMissionFeedContextValue = {
  events: [],
  unread: 0,
  busy: false,
  dismiss: async () => undefined,
  refresh: async () => undefined,
};

const OperatorMissionFeedContext = createContext<OperatorMissionFeedContextValue>(EMPTY);

/** Single poll loop shared by sidebar + mobile notification chrome. */
export function OperatorMissionFeedProvider({ children }: { children: ReactNode }): JSX.Element {
  const feed = useOperatorMissionFeed(true);
  useMissionSearchAutoBackfill(true);
  return (
    <OperatorMissionFeedContext.Provider value={feed}>{children}</OperatorMissionFeedContext.Provider>
  );
}

export function useOperatorMissionFeedContext(): OperatorMissionFeedContextValue {
  return useContext(OperatorMissionFeedContext);
}
