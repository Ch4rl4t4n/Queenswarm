"use client";

import { useEffect, useMemo, useState } from "react";

interface PaginatedSliceResult<T> {
  page: number;
  setPage: (page: number) => void;
  totalPages: number;
  totalItems: number;
  slice: T[];
}

/** Slice a list into fixed-size pages; clamps page when the list shrinks. */
export function usePaginatedSlice<T>(items: T[], pageSize: number, resetKey = ""): PaginatedSliceResult<T> {
  const [page, setPage] = useState(1);
  const totalItems = items.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

  useEffect(() => {
    setPage(1);
  }, [resetKey]);

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  const safePage = Math.min(Math.max(1, page), totalPages);

  const slice = useMemo(() => {
    const start = (safePage - 1) * pageSize;
    return items.slice(start, start + pageSize);
  }, [items, pageSize, safePage]);

  return {
    page: safePage,
    setPage,
    totalPages,
    totalItems,
    slice,
  };
}
