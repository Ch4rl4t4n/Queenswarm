"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

interface HiveMobileHeaderActionsContextValue {
  trailing: ReactNode;
  setTrailing: (node: ReactNode) => void;
}

const HiveMobileHeaderActionsContext = createContext<HiveMobileHeaderActionsContextValue | null>(null);

/** Shell provider — lets route clients inject icons beside the notification bell (< lg). */
export function HiveMobileHeaderActionsProvider({ children }: { children: ReactNode }): JSX.Element {
  const [trailing, setTrailing] = useState<ReactNode>(null);
  const value = useMemo(() => ({ trailing, setTrailing }), [trailing]);

  return <HiveMobileHeaderActionsContext.Provider value={value}>{children}</HiveMobileHeaderActionsContext.Provider>;
}

/** Read trailing actions rendered in the mobile header strip. */
export function useHiveMobileHeaderTrailing(): ReactNode {
  return useContext(HiveMobileHeaderActionsContext)?.trailing ?? null;
}

/** Mount page-specific trailing actions; cleared automatically on unmount. */
export function useSetHiveMobileHeaderTrailing(node: ReactNode): void {
  const ctx = useContext(HiveMobileHeaderActionsContext);

  useEffect(() => {
    if (!ctx) {
      return undefined;
    }
    ctx.setTrailing(node);
    return () => {
      ctx.setTrailing(null);
    };
  }, [ctx, node]);
}
