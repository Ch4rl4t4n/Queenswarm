import { Suspense } from "react";

import { BillingSettingsPanel } from "@/components/hive/billing-settings-panel";
import { V4Card } from "@/components/ui/v4";

function BillingLoadingFallback() {
  return (
    <V4Card>
      <p className="text-sm text-(--qs-text-3)">Loading billing…</p>
    </V4Card>
  );
}

export default function BillingSettingsPage() {
  return (
    <Suspense fallback={<BillingLoadingFallback />}>
      <BillingSettingsPanel />
    </Suspense>
  );
}
