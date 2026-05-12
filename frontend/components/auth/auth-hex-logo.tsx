import { cn } from "@/lib/utils";

interface AuthHexLogoProps {
  /** Additional classes on the root SVG. */
  className?: string;
}

/** Hive sigil — nested hex strokes with an abstract worker silhouette (vectors only). */
export function AuthHexLogo({ className }: AuthHexLogoProps) {
  return (
    <svg
      role="img"
      aria-label="Queenswarm hive glyph"
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("h-full w-full", className)}
    >
      <polygon
        points="32,4 58,18 58,46 32,60 6,46 6,18"
        className="fill-[#0d0d2b]"
        stroke="#FFB800"
        strokeWidth="2"
      />
      <polygon
        points="32,12 50,22 50,42 32,52 14,42 14,22"
        stroke="#FFB800"
        strokeWidth="0.6"
        className="fill-none opacity-[0.38]"
      />
      <ellipse cx="32" cy="36" rx="8" ry="10" stroke="#FFB800" strokeWidth="1.35" opacity="0.95" />
      <path
        d="M24 34c4-8 14-8 18 2"
        stroke="#FFB800"
        strokeWidth="1.1"
        strokeLinecap="round"
        opacity="0.9"
      />
      <circle cx="30" cy="33" r="2" fill="#FFB800" opacity="0.95" />
      <circle cx="36" cy="33" r="2" fill="#FFB800" opacity="0.95" />
      <ellipse cx="32" cy="25" rx="11" ry="7" stroke="#FFB800" strokeWidth="0.9" opacity="0.55" />
    </svg>
  );
}
