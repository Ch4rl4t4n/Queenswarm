import { redirect } from "next/navigation";

/** Legacy route — Costs live under Settings. */
export default function CostsLegacyRedirectPage() {
  redirect("/settings/costs");
}
