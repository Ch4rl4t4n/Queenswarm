"use client";

import { ChevronDown } from "lucide-react";
import { useId, useState, type ReactNode } from "react";

import { cn } from "@/lib/utils";

interface V4AdvancedPanelProps {
  title?: string;
  description?: string;
  children: ReactNode;
  defaultOpen?: boolean;
  className?: string;
}

/** Collapsible “Advanced” block — spawn forms & power-user controls. */
export function V4AdvancedPanel({
  title = "Advanced",
  description = "Spawn managers/workers and tune hive internals.",
  children,
  defaultOpen = false,
  className,
}: V4AdvancedPanelProps) {
  const [open, setOpen] = useState(defaultOpen);
  const baseId = useId();
  const triggerId = `${baseId}-trigger`;
  const regionId = `${baseId}-region`;

  return (
    <section className={cn("v4-card v4-card-interactive overflow-hidden p-0", className)}>
      <button
        type="button"
        id={triggerId}
        className="flex w-full items-center justify-between gap-3 px-6 py-4 text-left transition hover:bg-white/[0.04]"
        aria-expanded={open}
        aria-controls={open ? regionId : undefined}
        onClick={() => setOpen((v) => !v)}
      >
        <div>
          <p className="text-sm font-semibold text-(--qs-text)">{title}</p>
          <p className="mt-0.5 text-xs text-(--qs-text-3)">{description}</p>
        </div>
        <ChevronDown className={cn("h-5 w-5 shrink-0 text-(--qs-text-3) transition", open && "rotate-180")} aria-hidden />
      </button>
      {open ? (
        <div
          id={regionId}
          role="region"
          aria-labelledby={triggerId}
          className="border-t border-(--qs-border) px-6 py-5"
        >
          {children}
        </div>
      ) : null}
    </section>
  );
}
