"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  applySubnavOrder,
  loadSubnavOrder,
  mergeSubnavOrder,
  saveSubnavOrder,
} from "@/lib/subnav-order-preferences";

interface SubnavOrderItem {
  id: string;
}

function orderKeysEqual(a: readonly string[], b: readonly string[]): boolean {
  return a.length === b.length && a.every((id, index) => id === b[index]);
}

export function useSubnavOrder<T extends SubnavOrderItem>(
  menuKey: string | undefined,
  items: T[],
): {
  orderedItems: T[];
  unlocked: boolean;
  setUnlocked: (next: boolean) => void;
  reorderItems: (nextItems: T[]) => void;
  commitOrder: () => void;
  resetOrder: () => void;
} {
  const defaultIds = useMemo(() => items.map((item) => item.id), [items]);
  const defaultKey = defaultIds.join("|");

  const [unlocked, setUnlocked] = useState(false);
  const [order, setOrder] = useState<string[]>(() =>
    menuKey ? loadSubnavOrder(menuKey, defaultIds) : [...defaultIds],
  );

  useEffect(() => {
    const ids = defaultKey ? defaultKey.split("|") : [];
    if (!menuKey) {
      setOrder((prev) => (orderKeysEqual(prev, ids) ? prev : [...ids]));
      return;
    }
    const loaded = loadSubnavOrder(menuKey, ids);
    setOrder((prev) => (orderKeysEqual(prev, loaded) ? prev : loaded));
  }, [menuKey, defaultKey]);

  const orderedItems = useMemo(
    () => applySubnavOrder(items, menuKey ? order : defaultIds),
    [items, menuKey, order, defaultIds],
  );

  const persist = useCallback(
    (next: string[]) => {
      setOrder(next);
      if (menuKey) {
        saveSubnavOrder(menuKey, next);
      }
    },
    [menuKey],
  );

  const reorderItems = useCallback(
    (nextItems: T[]) => {
      const nextIds = nextItems.map((item) => item.id);
      const merged = mergeSubnavOrder(nextIds, defaultIds);
      setOrder((prev) => (orderKeysEqual(prev, merged) ? prev : merged));
    },
    [defaultIds],
  );

  const commitOrder = useCallback(() => {
    if (menuKey) {
      saveSubnavOrder(menuKey, order);
    }
  }, [menuKey, order]);

  const resetOrder = useCallback(() => {
    persist([...defaultIds]);
  }, [defaultIds, persist]);

  return { orderedItems, unlocked, setUnlocked, reorderItems, commitOrder, resetOrder };
}
