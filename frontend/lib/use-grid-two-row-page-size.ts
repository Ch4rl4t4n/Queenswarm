"use client";

import { useEffect, useState } from "react";

interface GridTwoRowPageSizeOptions {
  /** Grid columns at `md` and above. `3` → 6 items on wide screens; `2` → 4 items. */
  readonly columns?: 2 | 3;
  /** Min width for the third column tier (recipes catalog only). */
  readonly wideBreakpoint?: number;
}

/** Page size for exactly two visible grid rows (pagination-only lists). */
export function useGridTwoRowPageSize(options: GridTwoRowPageSizeOptions = {}): number {
  const columns = options.columns ?? 3;
  const wideBreakpoint = options.wideBreakpoint ?? 1280;
  const [pageSize, setPageSize] = useState(columns === 3 ? 6 : 4);

  useEffect(() => {
    const sync = (): void => {
      const width = window.innerWidth;
      if (columns === 3 && width >= wideBreakpoint) {
        setPageSize(6);
      } else if (width >= 640) {
        setPageSize(4);
      } else {
        setPageSize(2);
      }
    };
    sync();
    window.addEventListener("resize", sync);
    return () => window.removeEventListener("resize", sync);
  }, [columns, wideBreakpoint]);

  return pageSize;
}
