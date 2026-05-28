"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  dispatchSubnavVisibilityChange,
  loadSubnavDisabledIds,
  saveSubnavDisabledIds,
  SUBNAV_VISIBILITY_EVENT,
} from "@/lib/subnav-order-preferences";

export function useSubnavVisibility(menuKey: string | undefined, allIds: readonly string[]) {
  const [disabledIds, setDisabledIds] = useState<Set<string>>(() =>
    menuKey ? loadSubnavDisabledIds(menuKey) : new Set(),
  );

  useEffect(() => {
    if (!menuKey) {
      setDisabledIds(new Set());
      return;
    }
    const reload = (): void => {
      setDisabledIds(loadSubnavDisabledIds(menuKey));
    };
    reload();
    const onStorage = (event: StorageEvent): void => {
      if (event.key === null || event.key.includes(menuKey)) {
        reload();
      }
    };
    const onVisibility = (event: Event): void => {
      const detail = (event as CustomEvent<{ menuKey?: string }>).detail;
      if (detail?.menuKey === menuKey) {
        reload();
      }
    };
    window.addEventListener("storage", onStorage);
    window.addEventListener(SUBNAV_VISIBILITY_EVENT, onVisibility);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener(SUBNAV_VISIBILITY_EVENT, onVisibility);
    };
  }, [menuKey]);

  const enabledIds = useMemo(() => {
    const enabled = allIds.filter((id) => !disabledIds.has(id));
    return enabled.length > 0 ? enabled : [...allIds];
  }, [allIds, disabledIds]);

  const isDisabled = useCallback((id: string) => disabledIds.has(id), [disabledIds]);

  const disable = useCallback(
    (id: string): boolean => {
      if (!menuKey || !allIds.includes(id)) {
        return false;
      }
      const wouldEnable = allIds.filter((row) => !disabledIds.has(row) && row !== id);
      if (wouldEnable.length === 0) {
        return false;
      }
      const next = new Set(disabledIds);
      next.add(id);
      saveSubnavDisabledIds(menuKey, next);
      setDisabledIds(next);
      dispatchSubnavVisibilityChange(menuKey);
      return true;
    },
    [allIds, disabledIds, menuKey],
  );

  const enable = useCallback(
    (id: string): void => {
      if (!menuKey || !disabledIds.has(id)) {
        return;
      }
      const next = new Set(disabledIds);
      next.delete(id);
      saveSubnavDisabledIds(menuKey, next);
      setDisabledIds(next);
      dispatchSubnavVisibilityChange(menuKey);
    },
    [disabledIds, menuKey],
  );

  return {
    disabledIds,
    enabledIds,
    isDisabled,
    disable,
    enable,
    canDisable: enabledIds.length > 1,
  };
}
