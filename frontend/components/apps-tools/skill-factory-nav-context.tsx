"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

interface SkillFactoryNavState {
  queueBadge: number | undefined;
  setQueueBadge: (count: number | undefined) => void;
  packQueueBadge: number | undefined;
  setPackQueueBadge: (count: number | undefined) => void;
}

const SkillFactoryNavContext = createContext<SkillFactoryNavState | null>(null);

/** Lets factory pages surface queue counts on the layout subnav. */
export function SkillFactoryNavProvider({ children }: { children: ReactNode }): JSX.Element {
  const [queueBadge, setQueueBadge] = useState<number | undefined>(undefined);
  const [packQueueBadge, setPackQueueBadge] = useState<number | undefined>(undefined);
  const value = useMemo(
    () => ({ queueBadge, setQueueBadge, packQueueBadge, setPackQueueBadge }),
    [queueBadge, packQueueBadge],
  );
  return <SkillFactoryNavContext.Provider value={value}>{children}</SkillFactoryNavContext.Provider>;
}

export function useSkillFactoryNav(): SkillFactoryNavState {
  const ctx = useContext(SkillFactoryNavContext);
  if (!ctx) {
    return {
      queueBadge: undefined,
      setQueueBadge: () => undefined,
      packQueueBadge: undefined,
      setPackQueueBadge: () => undefined,
    };
  }
  return ctx;
}
