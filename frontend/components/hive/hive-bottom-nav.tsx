"use client";

import {
  EllipsisVerticalIcon,
  HexagonIcon,
  LayoutGridIcon,
  ListTodoIcon,
  MicIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

interface NavGlyphProps {
  label: string;
  Icon: typeof LayoutGridIcon;
  active: boolean;
}

function NavGlyph({ label, Icon, active }: NavGlyphProps) {
  return (
    <span
      className={cn(
        "flex min-w-[56px] flex-col items-center gap-1 py-2 text-[10px] font-semibold tracking-tight sm:text-[11px]",
        active ? "text-pollen" : "text-zinc-500",
      )}
    >
      <span
        className={cn(
          "rounded-2xl p-2 transition-[box-shadow,transform,color]",
          active
            ? "-translate-y-0.5 bg-pollen/[0.12] text-pollen shadow-[0_0_24px_rgb(255_184_0/0.42)]"
            : "text-zinc-500 hover:text-pollen",
        )}
      >
        <Icon aria-hidden className="h-[21px] w-[21px]" strokeWidth={active ? 2.35 : 1.9} />
      </span>
      {label}
    </span>
  );
}

interface HiveBottomNavProps {
  onMore: () => void;
}

const PRIMARY: readonly { href: string; label: string; Icon: typeof LayoutGridIcon }[] = [
  { href: "/", label: "Hive", Icon: LayoutGridIcon },
  { href: "/swarms", label: "Swarms", Icon: HexagonIcon },
  { href: "/tasks", label: "Tasks", Icon: ListTodoIcon },
  { href: "/ballroom", label: "Ballroom", Icon: MicIcon },
];

/** Thumb navigation — aligns with QueenSwarm mobile IA. */
export function HiveBottomNav({ onMore }: HiveBottomNavProps) {
  const pathname = usePathname();
  const moreActive =
    pathname.startsWith("/agents") ||
    pathname.startsWith("/workflows") ||
    pathname.startsWith("/recipes") ||
    pathname.startsWith("/leaderboard") ||
    pathname.startsWith("/costs") ||
    pathname.startsWith("/simulations") ||
    pathname.startsWith("/plugins") ||
    pathname.startsWith("/settings") ||
    pathname.startsWith("/design-system");

  return (
    <nav
      aria-label="Primary mobile navigation"
      className={cn(
        "fixed bottom-0 left-0 right-0 z-50 lg:hidden",
        "border-t border-cyan/[0.12] bg-[#08080f]/94 backdrop-blur-xl",
        "pb-[calc(0.35rem+env(safe-area-inset-bottom))] pt-1 shadow-[0_-18px_40px_rgb(0_0_0/0.45)]",
      )}
    >
      <div className="mx-auto flex max-w-xl items-center justify-between gap-0 px-1">
        {PRIMARY.map(({ href, label, Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link key={href} href={href} prefetch className="flex min-w-0 flex-1 justify-center touch-manipulation" aria-current={active ? "page" : undefined}>
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
          <NavGlyph label="More" Icon={EllipsisVerticalIcon} active={moreActive} />
        </button>
      </div>
    </nav>
  );
}
