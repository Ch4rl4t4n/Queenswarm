import { redirect } from "next/navigation";

import { hiveOverviewHref } from "@/lib/hive-home-route";

export default function HiveHomePage() {
  redirect(hiveOverviewHref());
}
