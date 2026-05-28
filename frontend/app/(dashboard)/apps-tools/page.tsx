import nextDynamic from "next/dynamic";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { V4Card, V4CardHeader } from "@/components/ui/v4";

const AppsToolsIndexClient = nextDynamic(
  () => import("@/components/apps-tools/apps-tools-index-client").then((mod) => ({ default: mod.AppsToolsIndexClient })),
  {
    loading: () => (
      <div className="space-y-4" data-testid="apps-tools-index-skeleton" role="status" aria-label="Loading modules">
        <div className="h-10 w-full max-w-md animate-pulse rounded-lg bg-white/5" />
        <div className="grid gap-3 sm:grid-cols-2">
          {Array.from({ length: 4 }, (_, index) => (
            <div key={`apps-tools-module-skel-${index}`} className="h-24 animate-pulse rounded-xl bg-white/[0.04]" />
          ))}
        </div>
      </div>
    ),
  },
);

export default function AppsToolsPage() {
  return (
    <HivePageShell
      title="Apps & Tools"
      subtitle="Modular workspace index. Each module is isolated by purpose and connected through capability contracts."
      hintKey="appsTools"
    >
      <V4Card>
        <V4CardHeader
          title="Module index"
          description="Compose-only route layer for the Agentic OS split. Existing execution flows stay unchanged and are opened through stable stubs."
        />
        <AppsToolsIndexClient />
      </V4Card>
    </HivePageShell>
  );
}
