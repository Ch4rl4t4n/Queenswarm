import { redirect } from "next/navigation";

import { SettingsPanelHost } from "@/components/hive/settings-panel-host";

interface SettingsSectionPageProps {
  params: Promise<{ section?: string[] }>;
}

export default async function SettingsSectionPage({ params }: SettingsSectionPageProps) {
  const { section } = await params;
  if (!section?.length) {
    redirect("/settings/security");
  }
  return <SettingsPanelHost />;
}
