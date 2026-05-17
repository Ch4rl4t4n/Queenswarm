"use client";

import { BellIcon, HexagonIcon, LogOutIcon, SearchIcon } from "lucide-react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";

import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { hiveGet } from "@/lib/api";
import type { OperatorCostSummary } from "@/lib/hive-types";
import { localizePhrase } from "@/lib/ui-copy";

interface HiveTopBarProps {
  email: string;
  displayName?: string | null;
}

function avatarLetters(displayName: string | null | undefined, email: string): string {
  const trimmed = displayName?.trim();
  if (trimmed) {
    const parts = trimmed.split(/\s+/).filter(Boolean);
    if (parts.length >= 2) {
      const a = parts[0]?.charAt(0) ?? "?";
      const b = parts[1]?.charAt(0) ?? "";
      return `${a}${b}`.toUpperCase();
    }
    return trimmed.slice(0, 2).toUpperCase();
  }
  const local = email.split("@")[0] ?? "?";
  return local.slice(0, 2).toUpperCase();
}

function latestDayUsd(series: OperatorCostSummary["series"]): number {
  if (!series.length) {
    return 0;
  }
  const sorted = [...series].sort((a, b) => a.day.localeCompare(b.day));
  const lastDay = sorted[sorted.length - 1]?.day;
  if (!lastDay) {
    return 0;
  }
  return sorted.filter((row) => row.day === lastDay).reduce((acc, row) => acc + row.spend_usd, 0);
}

/** Desktop cockpit chrome — gradient avatar + logout + hive search capsule. Mobile uses bottom-sheet actions. */
export function HiveTopBar({ email, displayName }: HiveTopBarProps) {
  const router = useRouter();
  const { language } = useUiLanguage();
  const [q, setQ] = useState("");
  const [time, setTime] = useState("");
  const [costTodayUsd, setCostTodayUsd] = useState<number | null>(null);

  useEffect(() => {
    const tick = (): void =>
      setTime(
        new Date().toLocaleTimeString("en-GB", {
          hour12: false,
        }),
      );
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void hiveGet<OperatorCostSummary>("operator/costs/summary?days=25")
      .then((costs) => {
        if (cancelled) {
          return;
        }
        const last = latestDayUsd(costs.series);
        setCostTodayUsd(last);
      })
      .catch(() => {
        if (!cancelled) {
          setCostTodayUsd(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function logout(): Promise<void> {
    try {
      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    } catch {
      /* ignore */
    }
    toast.success(localizePhrase(language, { en: "Session cleared", sk: "Relácia vyčistená" }));
    router.push("/login");
    router.refresh();
  }

  function onSearch(ev: FormEvent<HTMLFormElement>): void {
    ev.preventDefault();
    const term = q.trim();
    if (!term) {
      toast.message(localizePhrase(language, { en: "Search", sk: "Vyhľadávanie" }), {
        description: localizePhrase(language, { en: "Enter agents, tasks, or workflows.", sk: "Zadaj agentov, úlohy alebo workflowy." }),
      });
      return;
    }
    toast.message(localizePhrase(language, { en: "Hive search", sk: "Hive vyhľadávanie" }), {
      description:
        language === "sk"
          ? `Hľadám „${term}“ — proxy wiring je voliteľné.`
          : `Searching for “${term}” — proxy wiring optional.`,
    });
  }

  return (
    <header className="sticky top-0 z-40 hidden min-h-16 shrink-0 items-center gap-4 border-b border-cyan/[0.12] bg-[#050510]/95 px-6 py-2.5 backdrop-blur-md lg:flex">
      <Link href="/" className="flex items-center gap-2 pr-4" prefetch>
        <HexagonIcon className="h-6 w-6 text-pollen drop-shadow-[0_0_10px_rgb(255_184_0/0.55)]" aria-hidden />
        <span className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-[#fafafa]">QueenSwarm</span>
      </Link>

      <form onSubmit={onSearch} className="mx-auto min-w-0 max-w-xl flex-1">
        <label htmlFor="hive-search" className="sr-only">
          {localizePhrase(language, { en: "Search agents, tasks, workflows", sk: "Hľadaj agentov, úlohy, workflowy" })}
        </label>
        <div className="relative">
          <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" aria-hidden />
          <input
            id="hive-search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={localizePhrase(language, {
              en: "Search agents, tasks, workflows...",
              sk: "Hľadaj agentov, úlohy, workflowy...",
            })}
            className="w-full rounded-xl border border-cyan/[0.15] bg-black/55 py-2.5 pl-11 pr-4 font-[family-name:var(--font-poppins)] text-sm text-[#fafafa] placeholder:text-zinc-500 focus:border-pollen/35 focus:outline-none focus:ring-2 focus:ring-pollen/20"
          />
        </div>
      </form>

      <div className="hidden shrink-0 items-center gap-3 lg:flex">
        <span className="hidden font-[family-name:var(--font-poppins)] text-xs text-[#00FF88] sm:inline">{time}</span>
        <span className="flex items-center gap-1.5 font-[family-name:var(--font-poppins)] text-xs text-[#00FF88]">
          <span className="h-2 w-2 animate-pulse rounded-full bg-[#00FF88] shadow-[0_0_6px_#00FF88]" />
          <span className="hidden sm:inline">{localizePhrase(language, { en: "HIVE ONLINE", sk: "HIVE ONLINE" })}</span>
        </span>
        <span className="rounded-full border border-[#FF00AA]/30 bg-[#FF00AA]/10 px-2 py-1 font-[family-name:var(--font-poppins)] text-xs text-[#FF00AA]">
          💰{" "}
          {costTodayUsd === null
            ? "—"
            : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 }).format(
                costTodayUsd,
              )}{" "}
          {localizePhrase(language, { en: "today", sk: "dnes" })}
        </span>
      </div>

      <div className="ml-auto flex items-center gap-2">
        <button
          type="button"
          className="relative rounded-xl border border-cyan/[0.18] p-2.5 text-zinc-400 transition hover:border-pollen/35 hover:text-pollen"
          aria-label={localizePhrase(language, { en: "Notifications", sk: "Notifikácie" })}
          onClick={() =>
            toast.message(localizePhrase(language, { en: "Hive alerts", sk: "Hive upozornenia" }), {
              description: localizePhrase(language, { en: "Nothing unread.", sk: "Nič neprečítané." }),
            })
          }
        >
          <BellIcon className="h-4 w-4" aria-hidden />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-alert shadow-[0_0_8px_#FF00AA]" />
        </button>
        <div
          className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-orange-400 via-pollen to-[#FF6B9D] font-[family-name:var(--font-poppins)] text-[11px] font-bold uppercase text-black shadow-[0_0_20px_rgb(255_184_0/0.35)] ring-2 ring-black/70"
          title={displayName?.trim() || email}
        >
          {avatarLetters(displayName, email)}
        </div>
        <button
          type="button"
          onClick={() => void logout()}
          className="flex items-center gap-1.5 rounded-full border border-danger/35 px-3 py-2 font-[family-name:var(--font-poppins)] text-[10px] uppercase tracking-wide text-danger transition hover:bg-danger/12"
          aria-label={localizePhrase(language, { en: "Log out", sk: "Odhlásiť" })}
        >
          <LogOutIcon className="h-3.5 w-3.5" aria-hidden />
          {localizePhrase(language, { en: "out", sk: "odhlásiť" })}
        </button>
      </div>
    </header>
  );
}
