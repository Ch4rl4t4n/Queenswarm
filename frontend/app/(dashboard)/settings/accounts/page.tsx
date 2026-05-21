import dynamic from "next/dynamic";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const AdminAccountsSettingsPanel = dynamic(
  () =>
    import("@/components/hive/admin-accounts-settings-panel").then((mod) => ({
      default: mod.AdminAccountsSettingsPanel,
    })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export default function AdminAccountsSettingsPage() {
  return <AdminAccountsSettingsPanel />;
}
