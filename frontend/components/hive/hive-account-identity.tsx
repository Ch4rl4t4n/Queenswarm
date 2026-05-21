"use client";

import { BadgeCheck } from "lucide-react";

import { usePlatform } from "@/components/hive/platform-context";
import { UserStatusBadges } from "@/components/hive/user-status-badges";
import { buildUserStatusBadges } from "@/lib/user-status-badges";
import { cn } from "@/lib/utils";

interface HiveAccountIdentityProps {
  name: string;
  subtitle: string;
  language: "en" | "sk";
  className?: string;
  markClassName?: string;
}

/** Account row with avatar mark, title, subtitle, and tier/verified status bubbles. */
export function HiveAccountIdentity({ name, subtitle, language, className, markClassName }: HiveAccountIdentityProps) {
  const { subscriptionTier, platformMode, isAdmin, totpEnabled } = usePlatform();
  const badges = buildUserStatusBadges({
    language,
    subscriptionTier,
    platformMode,
    isAdmin,
    totpEnabled,
  });
  const initial = name.trim().charAt(0).toUpperCase() || "Q";
  const verifiedLabel = language === "sk" ? "Overený účet" : "Verified account";

  return (
    <div className={cn("flex min-w-0 items-start gap-3", className)}>
      <div className="relative shrink-0">
        <div className={cn("hive-tenant-mark", markClassName)}>{initial}</div>
        {totpEnabled ? (
          <BadgeCheck
            className="hive-tenant-verified-mark absolute -top-1 -right-1 h-[14px] w-[14px]"
            strokeWidth={2.75}
            aria-label={verifiedLabel}
          />
        ) : null}
      </div>
      <div className="hive-tenant-copy min-w-0">
        <span className="hive-tenant-title truncate">{name}</span>
        <span className="hive-tenant-sub truncate">{subtitle}</span>
        {badges.length > 0 ? <UserStatusBadges badges={badges} /> : null}
      </div>
    </div>
  );
}
