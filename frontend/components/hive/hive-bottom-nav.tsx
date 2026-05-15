"use client";

import type { LucideIcon } from "lucide-react";
import { EllipsisVerticalIcon } from "lucide-react";
import Link from "next/link";

import { hiveBottomNavItems, isNavItemActive } from "@/lib/hive-nav-primary";
import { cn } from "@/lib/utils";

interface NavGlyphProps {
  label: string;
  Icon: LucideIcon;
  active: boolean;
}

function NavGlyph({ label, Icon, active }: NavGlyphProps) {
  return (
    <span
      className={cn(
        "flex min-w-[52px] flex-col items-center gap-1 py-2 text-[10px] font-semibold tracking-tight sm:text-[11px]",
        active ? "text-pollen" : "text-zinc-500",
      )}
    >
      <span
        className={cn(
          "rounded-2xl p-2 transition-[box-shadow,transform,color] touch-manipulation min-h-[44px] min-w-[44px] flex items-center justify-center",
          active
            ? "-translate-y-0.5 bg-pollen/[0.12] text-pollen shadow-[0_0_24px_rgb(255_184_0/0.42)]"
            : "text-zinc-500 hover:text-pollen active:scale-95",
        )}
      >
        <Icon aria-hidden className="h-[21px] w-[21px]" strokeWidth={active ? 2.35 : 1.9} />
      </span>
      <span className="max-w-[68px] truncate text-center leading-tight">{label}</span>
    </span>
  );
}

interface HiveBottomNavProps {
  onMore: () => void;
  pathname: string;
}

/** Primary thumb targets — subset of nav + overflow sheet. */
export function HiveBottomNav({ onMore, pathname }: HiveBottomNavProps) {
  const items = hiveBottomNavItems();

  return (
    <nav
      aria-label="Primary mobile navigation"
      className={cn(
        "fixed bottom-0 left-0 right-0 z-50 lg:hidden",
        "border-t border-cyan/[0.12] bg-[#08080f]/94 backdrop-blur-xl",
        "pb-[calc(0.35rem+env(safe-area-inset-bottom))] pt-1 shadow-[0_-18px_40px_rgb(0_0_0/0.45)]",
      )}
    >
      <div className="mx-auto flex max-w-xl items-stretch justify-between gap-0 px-1">
        {items.map((item) => {
          const { href, label, Icon } = item;
          const active = isNavItemActive(pathname, item);
          return (
            <Link
              key={href}
              href={href}
              prefetch
              className="flex min-w-0 flex-1 justify-center touch-manipulation"
              aria-current={active ? "page" : undefined}
            >
              <NavGlyph label={label} Icon={Icon} active={active} />
            </Link>
          );
        })}
        <button
          type="button"
          className="flex min-w-0 flex-1 justify-center touch-manipulation"
          onClick={onMore}
          aria-haspopup="dialog"
        >
          <NavGlyph label="More" Icon={EllipsisVerticalIcon} active={false} />
        </button>
      </div>
    </nav>
  );
}
