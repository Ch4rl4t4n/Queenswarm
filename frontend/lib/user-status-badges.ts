import type { PlatformMode } from "@/lib/platform-features";

export type UserStatusBadgeTone = "amber" | "green" | "cyan" | "muted";

export interface UserStatusBadgeDef {
  key: string;
  label: string;
  tone: UserStatusBadgeTone;
}

const TIER_LABELS: Record<string, { en: string; sk: string }> = {
  free: { en: "Regular", sk: "Regular" },
  starter: { en: "Starter", sk: "Starter" },
  pro: { en: "Pro", sk: "Pro" },
  premium: { en: "Premium", sk: "Premium" },
  enterprise: { en: "Enterprise", sk: "Enterprise" },
};

/** Operator-facing account badges for nav / session menus. */
export function buildUserStatusBadges(opts: {
  language: "en" | "sk";
  subscriptionTier: string;
  platformMode: PlatformMode;
  isAdmin: boolean;
  totpEnabled: boolean;
}): UserStatusBadgeDef[] {
  const badges: UserStatusBadgeDef[] = [];
  const tier = String(opts.subscriptionTier ?? "free").trim().toLowerCase();

  // Operator role is already reflected in the subtitle ("Owner · operator"); skip duplicate pill.
  if (!(opts.platformMode === "internal" && opts.isAdmin)) {
    const tierLabel = TIER_LABELS[tier] ?? TIER_LABELS.free;
    badges.push({
      key: "tier",
      label: tierLabel[opts.language],
      tone: "amber",
    });
  }

  // Verified state is surfaced as an inline check icon next to the name (see HiveAccountIdentity).
  return badges;
}
