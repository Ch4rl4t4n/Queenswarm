import { HivePageHeader } from "@/components/hive/hive-page-header";
import { PatternExplorerSettingsPanel } from "@/components/hive/pattern-explorer-card";
import { SettingsHarnessPanel } from "@/components/hive/settings-harness-panel";
import { V4PageCanvas } from "@/components/ui/v4";

export default function HarnessSettingsPage(): JSX.Element {
  return (
    <V4PageCanvas>
      <HivePageHeader
        title="AI harness"
        subtitle="Rules · skills · MCP · pattern telemetry · behavioral memory"
      />
      <SettingsHarnessPanel />
      <div className="mt-8">
        <PatternExplorerSettingsPanel />
      </div>
    </V4PageCanvas>
  );
}
