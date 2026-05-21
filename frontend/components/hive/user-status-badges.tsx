import type { UserStatusBadgeDef } from "@/lib/user-status-badges";
import { cn } from "@/lib/utils";

interface UserStatusBadgesProps {
  badges: UserStatusBadgeDef[];
  className?: string;
}

/** Pill status bubbles under account identity (tier, verified, operator). */
export function UserStatusBadges({ badges, className }: UserStatusBadgesProps) {
  if (!badges.length) {
    return null;
  }

  return (
    <div className={cn("hive-user-status-badges", className)} aria-label="Account status">
      {badges.map((badge) => (
        <span
          key={badge.key}
          className={cn(
            "hive-user-status-badge",
            badge.tone === "amber" && "hive-user-status-badge--amber",
            badge.tone === "green" && "hive-user-status-badge--green",
            badge.tone === "cyan" && "hive-user-status-badge--cyan",
            badge.tone === "muted" && "hive-user-status-badge--muted",
          )}
        >
          {badge.label}
        </span>
      ))}
    </div>
  );
}
