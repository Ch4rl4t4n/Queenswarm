import dynamic from "next/dynamic";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const CommandCenterSettingsPanel = dynamic(
  () =>
    import("@/components/hive/command-center-settings-panel").then((mod) => ({
      default: mod.CommandCenterSettingsPanel,
    })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export default function CommandCenterSettingsPage() {
  return <CommandCenterSettingsPanel />;
}
