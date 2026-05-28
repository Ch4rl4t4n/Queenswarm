"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { BILLING_PLANS_HASH } from "@/lib/billing-settings-copy";

/** Legacy `/settings/billing` — client redirect preserves `#billing-plans` deep link. */
export default function SettingsBillingLegacyPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace(`/settings/costs#${BILLING_PLANS_HASH}`);
  }, [router]);

  return <p className="text-sm text-(--qs-text-3)">Redirecting to Costs…</p>;
}
