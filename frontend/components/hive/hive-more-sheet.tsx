"use client";

import { LockIcon, LogOutIcon, XIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { toast } from "sonner";

import { HIVE_NAV_GROUPS, isNavItemActive } from "@/lib/hive-nav-primary";
import { cn } from "@/lib/utils";

interface HiveMoreSheetProps {
  open: boolean;
  onClose: () => void;
  pathname: string;
}

/** Full IA overflow — grouped routes + account actions (mobile / tablet). */
export function HiveMoreSheet({ open, onClose, pathname }: HiveMoreSheetProps) {
  const router = useRouter();

  useEffect(() => {
    if (!open) {
      return;
    }
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  async function logout(): Promise<void> {
    try {
      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    } catch {
      /* ignore */
    }
    toast.success("Logged out");
    onClose();
    router.push("/login");
    router.refresh();
  }

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[60] flex flex-col justify-end lg:hidden">
      <button type="button" className="absolute inset-0 bg-black/72 backdrop-blur-sm" aria-label="Close menu" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="hive-more-sheet-title"
        className="relative mx-auto flex max-h-[min(88vh,640px)] w-full max-w-lg flex-col rounded-t-3xl border border-cyan/[0.15] bg-[#0f0f16] shadow-[0_-24px_64px_rgb(0_0_0/0.55)]"
      >
        <div className="relative flex flex-col items-center px-4 pt-3">
          <span className="mb-2 h-1 w-14 rounded-full bg-zinc-600" aria-hidden />
          <button
            type="button"
            aria-label="Close sheet"
            className="absolute right-3 top-2 rounded-lg border border-cyan/[0.15] p-2 text-zinc-400 hover:text-pollen touch-manipulation min-h-[44px] min-w-[44px]"
            onClick={onClose}
          >
            <XIcon className="h-4 w-4" aria-hidden />
          </button>
        </div>

        <h2 id="hive-more-sheet-title" className="px-6 pb-2 pt-1 font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#fafafa]">
          Hive navigation
        </h2>

        <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-2 hive-scrollbar">
          {HIVE_NAV_GROUPS.map((group) => (
            <div key={group.title} className="mb-4">
              <p className="px-3 pb-2 font-mono text-[10px] uppercase tracking-[0.28em] text-zinc-600">{group.title}</p>
              <ul className="space-y-1">
                {group.items.map((item) => {
                  const { href, label, Icon } = item;
                  const active = isNavItemActive(pathname, item);
                  return (
                    <li key={`${group.title}-${href}`}>
                      <Link
                        href={href}
                        prefetch
                        onClick={onClose}
                        className={cn(
                          "flex items-center gap-3 rounded-2xl px-4 py-3 font-[family-name:var(--font-poppins)] text-sm transition touch-manipulation min-h-[48px]",
                          active ? "bg-pollen/12 text-pollen shadow-[inset_0_0_0_1px_rgb(255_184_0/0.25)]" : "text-zinc-300 hover:bg-white/[0.04]",
                        )}
                      >
                        <Icon className={cn("h-5 w-5 shrink-0", active ? "text-pollen" : "text-zinc-500")} aria-hidden />
                        <span>{label}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        <div className="border-t border-[#1e2348] px-3 pb-[calc(1rem+env(safe-area-inset-bottom))] pt-2">
          <p className="px-3 pb-2 font-mono text-[10px] uppercase tracking-[0.28em] text-zinc-600">Session</p>
          <ul className="space-y-1">
            <li>
              <button
                type="button"
                className="flex w-full min-h-[48px] items-center gap-4 rounded-2xl px-4 py-3 text-left font-[family-name:var(--font-poppins)] text-sm text-zinc-300 transition hover:bg-white/[0.04] touch-manipulation"
                onClick={() => {
                  onClose();
                  router.push("/login");
                }}
              >
                <LockIcon className="h-5 w-5 shrink-0 text-pollen" aria-hidden />
                Login screen
              </button>
            </li>
            <li>
              <button
                type="button"
                className="flex w-full min-h-[48px] items-center gap-4 rounded-2xl px-4 py-3 text-left font-[family-name:var(--font-poppins)] text-sm text-danger transition hover:bg-danger/[0.08] touch-manipulation"
                onClick={() => void logout()}
              >
                <LogOutIcon className="h-5 w-5 shrink-0" aria-hidden />
                Log out
              </button>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
