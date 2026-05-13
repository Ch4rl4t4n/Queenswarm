import type { LucideIcon } from "lucide-react";

interface WidgetStatProps {
  label: string;
  value: string;
  caption?: string;
  icon: LucideIcon;
}

export function WidgetStat({ label, value, caption, icon: Icon }: WidgetStatProps) {
  return (
    <article className="hex-card relative overflow-hidden rounded-2xl border border-cyan/20 bg-gradient-to-br from-[#090919] via-[#060612] to-[#04040d] p-5 shadow-[0_18px_40px_rgba(0,0,0,0.55)]">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(120deg,rgba(0,255,255,0.08),transparent)]" />
      <div className="relative flex items-start gap-4">
        <Icon className="mt-1 h-8 w-8 text-[#FFB800]" aria-hidden />
        <div className="space-y-1">
          <p className="font-[family-name:var(--font-poppins)] text-xs uppercase tracking-[0.2em] text-cyan/80">
            {label}
          </p>
          <p className="font-[family-name:var(--font-poppins)] text-3xl font-semibold tracking-tight text-pollen shadow-[0_0_35px_rgba(255,184,0,0.42)]">
            {value}
          </p>
          {caption ? (
            <p className="font-[family-name:var(--font-poppins)] text-[11px] text-[#00FF88]/80">
              {caption}
            </p>
          ) : null}
        </div>
      </div>
    </article>
  );
}
