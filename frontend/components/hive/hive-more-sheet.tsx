"use client";

import {
  BadgeDollarSignIcon,
  BookOpenIcon,
  BotIcon,
  FlaskConicalIcon,
  GitBranchIcon,
  LockIcon,
  LogOutIcon,
  PaletteIcon,
  PuzzleIcon,
  SettingsIcon,
  TrophyIcon,
  XIcon,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { toast } from "sonner";

interface HiveMoreSheetProps {
  open: boolean;
  onClose: () => void;
}

const LINKS = [
  { href: "/agents", label: "Agents", Icon: BotIcon },
  { href: "/workflows", label: "Workflows", Icon: GitBranchIcon },
  { href: "/recipes", label: "Recipes", Icon: BookOpenIcon },
  { href: "/leaderboard", label: "Leaderboard", Icon: TrophyIcon },
  { href: "/costs", label: "Costs", Icon: BadgeDollarSignIcon },
  { href: "/settings/profile", label: "Settings", Icon: SettingsIcon },
] as const;

/** Bottom sheet with secondary IA + labs — blurred scrim per mobile mock. */
export function HiveMoreSheet({ open, onClose }: HiveMoreSheetProps) {
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
    toast.success("Session cleared");
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
        className="relative mx-auto w-full max-w-lg rounded-t-3xl border border-cyan/[0.15] bg-[#0f0f16] pb-[calc(1.25rem+env(safe-area-inset-bottom))] shadow-[0_-24px_64px_rgb(0_0_0/0.55)]"
      >
        <div className="relative flex flex-col items-center px-4 pt-3">
          <span className="mb-2 h-1 w-14 rounded-full bg-zinc-600" aria-hidden />
          <button
            type="button"
            aria-label="Zavrieť ponuku"
            className="absolute right-3 top-2 rounded-lg border border-cyan/[0.15] p-2 text-zinc-400 hover:text-pollen"
            onClick={onClose}
          >
            <XIcon className="h-4 w-4" aria-hidden />
          </button>
        </div>

        <h2 id="hive-more-sheet-title" className="px-6 pb-3 pt-1 font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">
          All screens
        </h2>

        <ul className="max-h-[60vh] space-y-0.5 overflow-y-auto px-3 hive-scrollbar pb-2">
          {LINKS.map(({ href, label, Icon }) => (
            <li key={href}>
              <Link
                href={href}
                prefetch
                onClick={onClose}
                className="flex items-center gap-4 rounded-2xl px-4 py-3.5 font-[family-name:var(--font-inter)] text-[15px] text-[#fafafa] transition hover:bg-white/[0.05]"
              >
                <Icon className="h-5 w-5 shrink-0 text-pollen/90" aria-hidden />
                {label}
              </Link>
            </li>
          ))}
        </ul>

        <div className="mx-4 my-2 h-px bg-cyan/[0.08]" />

        <ul className="space-y-0.5 px-3 pb-4">
          <li>
            <Link
              href="/simulations"
              prefetch
              onClick={onClose}
              className="flex items-center gap-4 rounded-2xl px-4 py-3.5 font-[family-name:var(--font-inter)] text-sm text-zinc-400 transition hover:bg-white/[0.04]"
            >
              <FlaskConicalIcon className="h-5 w-5 shrink-0 text-data" aria-hidden />
              Simulations
            </Link>
          </li>
          <li>
            <Link
              href="/design-system"
              prefetch
              onClick={onClose}
              className="flex items-center gap-4 rounded-2xl px-4 py-3.5 font-[family-name:var(--font-inter)] text-sm text-zinc-400 transition hover:bg-white/[0.04]"
            >
              <PaletteIcon className="h-5 w-5 shrink-0 text-pollen/90" aria-hidden />
              Design system
            </Link>
          </li>
          <li>
            <Link
              href="/plugins"
              prefetch
              onClick={onClose}
              className="flex items-center gap-4 rounded-2xl px-4 py-3.5 font-[family-name:var(--font-inter)] text-sm text-zinc-400 transition hover:bg-white/[0.04]"
            >
              <PuzzleIcon className="h-5 w-5 shrink-0 text-cyan" aria-hidden />
              Plugins
            </Link>
          </li>
          <li>
            <button
              type="button"
              className="flex w-full items-center gap-4 rounded-2xl px-4 py-3.5 text-left font-[family-name:var(--font-inter)] text-sm text-zinc-300 transition hover:bg-white/[0.04]"
              onClick={() => {
                onClose();
                router.push("/login");
              }}
            >
              <LockIcon className="h-5 w-5 shrink-0 text-pollen" aria-hidden />
              Show login screen
            </button>
          </li>
          <li>
            <button
              type="button"
              className="flex w-full items-center gap-4 rounded-2xl px-4 py-3.5 text-left font-[family-name:var(--font-inter)] text-sm text-danger transition hover:bg-danger/[0.08]"
              onClick={() => void logout()}
            >
              <LogOutIcon className="h-5 w-5 shrink-0" aria-hidden />
              Log out
            </button>
          </li>
        </ul>
      </div>
    </div>
  );
}
