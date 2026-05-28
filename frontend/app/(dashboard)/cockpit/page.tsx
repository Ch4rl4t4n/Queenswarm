import { CockpitLegacyRedirect } from "@/components/hive/cockpit-legacy-redirect";

/** Legacy bookmark — client redirect preserves `#section` deep links. */
export default function CockpitLegacyPage() {
  return <CockpitLegacyRedirect />;
}
