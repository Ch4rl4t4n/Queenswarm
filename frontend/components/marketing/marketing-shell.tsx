import Link from "next/link";
import type { ReactNode } from "react";

import { appPublicOrigin, marketingPublicOrigin } from "@/lib/marketing-host";

interface MarketingShellProps {
  readonly children: ReactNode;
}

export function MarketingShell({ children }: MarketingShellProps): JSX.Element {
  const appOrigin = appPublicOrigin();

  return (
    <div className="min-h-screen bg-(--qs-bg) text-(--qs-text)">
      <header className="border-b border-(--qs-border) bg-(--qs-surface-3)/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4">
          <Link href="/" className="font-[family-name:var(--font-hive-display)] text-lg font-bold text-pollen">
            Let Agents Cook
          </Link>
          <nav className="flex items-center gap-3 text-sm">
            <Link href="/skills" className="text-(--qs-text-2) hover:text-cyan">
              Skills
            </Link>
            <a href={`${appOrigin}/login`} className="qs-btn qs-btn--ghost qs-btn--sm">
              Open app
            </a>
          </nav>
        </div>
      </header>
      <main>{children}</main>
      <footer className="border-t border-(--qs-border) px-4 py-10 text-sm text-(--qs-text-3)">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <p>Verified agent skills and content packs — simulate-first, sell with confidence.</p>
          <p>
            Powered by{" "}
            <a href={appOrigin} className="text-cyan underline-offset-2 hover:underline">
              Queenswarm
            </a>{" "}
            · {marketingPublicOrigin().replace("https://", "")}
          </p>
        </div>
      </footer>
    </div>
  );
}
