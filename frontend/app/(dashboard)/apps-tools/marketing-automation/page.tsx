import type { Route } from "next";
import { redirect } from "next/navigation";

interface MarketingAutomationLegacyRedirectPageProps {
  searchParams: Promise<{ section?: string | string[] }>;
}

export default async function MarketingAutomationLegacyRedirectPage({
  searchParams,
}: MarketingAutomationLegacyRedirectPageProps) {
  const params = await searchParams;
  const sectionRaw = params.section;
  const section = Array.isArray(sectionRaw) ? sectionRaw[0] : sectionRaw;
  const mapped =
    section === "queue" ||
    section === "publish" ||
    section === "performance" ||
    section === "launch"
      ? section
      : "calendar";
  redirect(
    `/apps-tools/marketing-team?section=${encodeURIComponent(mapped)}` as Route,
  );
}
