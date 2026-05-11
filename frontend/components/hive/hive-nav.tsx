import Link from "next/link";
import { HexagonIcon } from "lucide-react";

const ROUTES = [
  { href: "/", label: "hive" },
  { href: "/agents", label: "agents" },
  { href: "/swarms", label: "swarms" },
  { href: "/tasks", label: "tasks" },
  { href: "/workflows", label: "workflows" },
  { href: "/recipes", label: "recipes" },
  { href: "/leaderboard", label: "leaderboard" },
  { href: "/simulations", label: "simulations" },
  { href: "/ballroom", label: "ballroom" },
  { href: "/plugins", label: "plugins" },
  { href: "/costs", label: "costs" },
] as const;

export function HiveNav() {
  return (
    <header className="sticky top-0 z-50 border-b border-cyan/20 bg-[#050510]/85 backdrop-blur-lg">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-3 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
        <Link
          href="/"
          className="flex items-center gap-2 font-[family-name:var(--font-space-grotesk)] text-xl font-semibold tracking-wide text-pollen shadow-[0_0_26px_rgba(255,184,0,0.55)]"
        >
          <HexagonIcon aria-hidden className="h-7 w-7 text-[#00FFFF]" />
          Queenswarm
        </Link>
        <nav
          aria-label="Hive routes"
          className="flex flex-wrap gap-x-4 gap-y-2 font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase tracking-widest text-data"
        >
          {ROUTES.map((r) => (
            <Link
              key={r.href}
              href={r.href}
              prefetch
              className="rounded-full border border-cyan/20 px-3 py-1 text-[10px] text-cyan transition hover:border-pollen hover:text-pollen"
            >
              {r.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
