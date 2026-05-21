"use client";

import { useEffect, useRef } from "react";

import { isHiveApiRateLimited } from "@/lib/api";
import { isHiveSessionDead } from "@/lib/hive-session-guard";
import { useDocumentVisible } from "@/lib/hooks/use-document-visible";

interface UseIntervalWhenVisibleOptions {
  /** When false, interval is not scheduled. Default true. */
  enabled?: boolean;
  /** Fire once when the tab becomes visible or on mount. Default true. */
  runImmediately?: boolean;
  /** Delay before the first immediate run (ms). Default 0. */
  initialDelayMs?: number;
}

/**
 * Schedule `callback` on a fixed interval only while the document tab is visible.
 * Pauses timers in background tabs to reduce VPS load.
 */
export function useIntervalWhenVisible(
  callback: () => void,
  intervalMs: number | null,
  options?: UseIntervalWhenVisibleOptions,
): void {
  const enabled = options?.enabled ?? true;
  const runImmediately = options?.runImmediately ?? true;
  const initialDelayMs = options?.initialDelayMs ?? 0;
  const visible = useDocumentVisible();
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled || intervalMs === null || intervalMs <= 0) {
      return undefined;
    }

    let delayHandle: number | undefined;

    const run = (): void => {
      if (document.visibilityState !== "visible" || isHiveApiRateLimited() || isHiveSessionDead()) {
        return;
      }
      savedCallback.current();
    };

    if (visible && runImmediately) {
      if (initialDelayMs > 0) {
        delayHandle = window.setTimeout(run, initialDelayMs);
      } else {
        run();
      }
    }

    if (!visible) {
      return () => {
        if (delayHandle !== undefined) {
          window.clearTimeout(delayHandle);
        }
      };
    }

    const handle = window.setInterval(run, intervalMs);

    return () => {
      if (delayHandle !== undefined) {
        window.clearTimeout(delayHandle);
      }
      window.clearInterval(handle);
    };
  }, [enabled, initialDelayMs, intervalMs, runImmediately, visible]);
}
