import { DashboardSectionSkeleton } from "@/components/hive/colony-console-skeleton";
import { V4PageCanvas } from "@/components/ui/v4";

export default function HarnessSettingsLoading(): JSX.Element {
  return (
    <V4PageCanvas>
      <DashboardSectionSkeleton className="min-h-[320px]" />
    </V4PageCanvas>
  );
}
