import { TargetIcon } from "lucide-react";

import { V4Stat } from "@/components/ui/v4";
import { costsBillingPlansHref } from "@/lib/billing-settings-copy";

/** KPI tile on Costs — jumps to embedded plan comparison (`#billing-plans`). */
export function CostsTierLimitsKpi() {
  return (
    <V4Stat
      href={costsBillingPlansHref()}
      linkLabel="Tier limits — view plan comparison"
      label="Tier limits"
      value="Plans"
      icon={TargetIcon}
      iconTone="purple"
      foot="Soft/hard caps · view plans"
    />
  );
}
