import nextDynamic from "next/dynamic";
import { redirect } from "next/navigation";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";
import { PHASE70_CONSOLIDATED_NAV_ENABLED, RECIPES_ENABLED } from "@/lib/feature-flags";

const RecipesPageClient = nextDynamic(
  () => import("@/components/hive/recipes-page-client").then((mod) => ({ default: mod.RecipesPageClient })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function RecipesPage() {
  if (PHASE70_CONSOLIDATED_NAV_ENABLED) {
    redirect("/knowledge#recipes");
  }

  if (!RECIPES_ENABLED) {
    return (
      <div className="rounded-2xl border border-cyan/20 bg-black/30 p-5">
        <p className="font-(family-name:--font-poppins) text-sm text-zinc-300">
          Recipes module is disabled. Enable <code>NEXT_PUBLIC_RECIPES_ENABLED=true</code> to open this page.
        </p>
      </div>
    );
  }
  return <RecipesPageClient />;
}
