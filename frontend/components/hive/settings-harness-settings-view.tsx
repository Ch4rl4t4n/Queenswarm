import { HivePageHeader } from "@/components/hive/hive-page-header";
import { PatternExplorerSettingsPanel } from "@/components/hive/pattern-explorer-card";
import { SettingsHarnessPanel } from "@/components/hive/settings-harness-panel";
import { SettingsOperatorHubPanel } from "@/components/hive/settings-operator-hub-panel";
import { V4PageCanvas } from "@/components/ui/v4";

/** Harness settings section — preserved layout from legacy route page. */
export function SettingsHarnessSettingsView(): JSX.Element {
  return (
    <V4PageCanvas>
      <HivePageHeader
        title="AI harness"
        subtitle="Rules · skills · MCP · pattern telemetry · behavioral memory"
      />
      <div className="mb-8">
        <SettingsOperatorHubPanel />
      </div>
      <SettingsHarnessPanel />
      <div className="mt-8">
        <PatternExplorerSettingsPanel />
      </div>
    </V4PageCanvas>
  );
}
