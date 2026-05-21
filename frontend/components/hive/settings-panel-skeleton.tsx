import { Loader2Icon } from "lucide-react";

import { V4Card } from "@/components/ui/v4";

export function SettingsPanelSkeleton() {
  return (
    <V4Card className="flex min-h-[220px] items-center justify-center">
      <Loader2Icon className="h-6 w-6 animate-spin text-pollen" aria-hidden />
    </V4Card>
  );
}
