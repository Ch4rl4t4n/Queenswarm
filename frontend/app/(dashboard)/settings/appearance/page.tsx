import Link from "next/link";

import { NeonButton } from "@/components/ui/neon-button";

export default function SettingsAppearancePage() {
  return (
    <article className="rounded-2xl border border-cyan/[0.12] bg-hive-card/90 p-6 md:p-8">
      <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">Appearance</h2>
      <p className="mt-4 max-w-lg font-[family-name:var(--font-inter)] text-sm leading-relaxed text-muted-foreground">
        Použi plávajúci panel Tweaks na live úpravu akcentov, glow, hex štýlu a hustoty vzoru — zosúladené so Space Grotesk
        + neon-dark tokami.
      </p>
      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <NeonButton variant="primary" asChild className="w-fit">
          <Link href="/design-system">Tokeny a komponenty (Design system)</Link>
        </NeonButton>
        <p className="font-[family-name:var(--font-inter)] text-xs text-zinc-500">
          V menu: Labs → Design system · URL <span className="font-mono text-cyan/80">/design-system</span>
        </p>
      </div>
    </article>
  );
}
