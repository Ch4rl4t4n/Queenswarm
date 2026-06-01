"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { HiveApiError, hiveGet } from "@/lib/api";

export interface MissionSearchSessionHit {
  session_id: string;
  status: string;
  goal_excerpt: string;
  match_source: string;
  snippet: string;
  created_at?: string | null;
}

export interface MissionSearchTaskHit {
  task_id: string;
  title: string;
  status: string;
  match_source: string;
  updated_at?: string | null;
}

export interface MissionSearchResult {
  query: string;
  sessions: MissionSearchSessionHit[];
  tasks: MissionSearchTaskHit[];
  total: number;
}

const EMPTY: MissionSearchResult = {
  query: "",
  sessions: [],
  tasks: [],
  total: 0,
};

export function useMissionSearch(debounceMs = 280): {
  query: string;
  setQuery: (value: string) => void;
  result: MissionSearchResult;
  busy: boolean;
  error: string | null;
  searchNow: () => Promise<void>;
} {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<MissionSearchResult>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const searchNow = useCallback(async () => {
    const q = query.trim();
    if (q.length < 2) {
      setResult(EMPTY);
      setError(null);
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setBusy(true);
    try {
      const body = await hiveGet<MissionSearchResult>(
        `solo-operator/mission-search?q=${encodeURIComponent(q)}&session_limit=10&task_limit=10`,
        { signal: controller.signal },
      );
      if (controller.signal.aborted) return;
      setResult(body);
      setError(null);
    } catch (e) {
      if (controller.signal.aborted) return;
      setError(e instanceof HiveApiError ? e.message : "Search failed");
      setResult(EMPTY);
    } finally {
      if (!controller.signal.aborted) {
        setBusy(false);
      }
    }
  }, [query]);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setResult(EMPTY);
      setError(null);
      return undefined;
    }
    const timer = window.setTimeout(() => {
      void searchNow();
    }, debounceMs);
    return () => window.clearTimeout(timer);
  }, [query, debounceMs, searchNow]);

  return { query, setQuery, result, busy, error, searchNow };
}
