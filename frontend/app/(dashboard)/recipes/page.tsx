import { RecipesPageClient } from "@/components/hive/recipes-page-client";
import { RECIPES_ENABLED } from "@/lib/feature-flags";

export const dynamic = "force-dynamic";

export default function RecipesPage() {
  if (!RECIPES_ENABLED) {
    return (
      <div className="rounded-2xl border border-cyan/20 bg-black/30 p-5">
        <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-300">
          Recipes module is disabled. Enable <code>NEXT_PUBLIC_RECIPES_ENABLED=true</code> to open this page.
        </p>
      </div>
    );
  }
  return <RecipesPageClient />;
}
