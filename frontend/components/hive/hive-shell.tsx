import type { ReactNode } from "react";

import { HiveNav } from "@/components/hive/hive-nav";

interface HiveShellProps {
  children: ReactNode;
}

export function HiveShell({ children }: HiveShellProps) {
  return (
    <div className="hive-shell flex min-h-screen flex-col bg-hive-bg text-pollen">
      <HiveNav />
      <div className="pointer-events-none fixed inset-x-0 top-28 -z-10 h-96 bg-[radial-gradient(circle_at_top,_rgba(0,255,255,0.14),transparent_62%)]" />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 pb-20 pt-8">{children}</main>
      <footer className="border-t border-cyan/10 py-8 text-center font-[family-name:var(--font-jetbrains-mono)] text-xs text-cyan/60">
        queenswarm · global sync cadence · rapid loop verified payloads only
      </footer>
    </div>
  );
}
