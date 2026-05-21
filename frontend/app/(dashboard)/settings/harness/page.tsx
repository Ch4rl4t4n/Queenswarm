import { HivePageHeader } from "@/components/hive/hive-page-header";
import { PatternExplorerSettingsPanel } from "@/components/hive/pattern-explorer-card";
import { V4PageCanvas } from "@/components/ui/v4";

export default function HarnessSettingsPage(): JSX.Element {
  return (
    <V4PageCanvas>
      <HivePageHeader
        title="AI harness"
        subtitle="Pattern Explorer · Kashef agentic design pattern catalog"
      />
      <PatternExplorerSettingsPanel />
    </V4PageCanvas>
  );
}
