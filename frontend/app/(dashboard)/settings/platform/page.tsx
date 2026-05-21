import dynamic from "next/dynamic";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const PlatformFeaturesSettingsPanel = dynamic(
  () =>
    import("@/components/hive/platform-features-settings-panel").then((mod) => ({
      default: mod.PlatformFeaturesSettingsPanel,
    })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export default function PlatformFeaturesSettingsPage() {
  return <PlatformFeaturesSettingsPanel />;
}
