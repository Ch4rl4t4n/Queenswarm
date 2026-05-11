import { hiveServerRawJson } from "@/lib/hive-server";
import type { RecipeRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

export default async function RecipesPage() {
  const catalog = await hiveServerRawJson<RecipeRow[]>("/recipes?verified_only=true&limit=50");

  if (!catalog) {
    return (
      <p className="text-danger font-[family-name:var(--font-jetbrains-mono)] text-sm">
        Recipe Library offline — Chrom + Postgres linkage required for semantic recall.
      </p>
    );
  }

  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-[family-name:var(--font-space-grotesk)] text-3xl font-semibold text-pollen">
          verified recipe codex
        </h1>
        <p className="mt-3 max-w-3xl font-[family-name:var(--font-jetbrains-mono)] text-sm text-cyan">
          Every swarm-proven playbook snapshot gets mirrored here for imitation cosine ≥ library threshold (default 0.85).
        </p>
      </header>
      <div className="grid gap-4 md:grid-cols-2">
        {catalog.map((recipe) => (
          <article key={recipe.id} className="rounded-3xl border border-success/35 bg-black/35 p-5 shadow-[0_0_42px_rgba(0,255,136,0.15)]">
            <p className="font-[family-name:var(--font-space-grotesk)] text-2xl font-semibold tracking-tight text-pollen">{recipe.name}</p>
            <p className="mt-3 text-sm leading-relaxed text-[#EAFFFF]/90">{recipe.description}</p>
            <div className="mt-4 flex flex-wrap gap-2 font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase tracking-[0.2em] text-data">
              {(recipe.topic_tags ?? []).map((tag) => (
                <span key={tag} className="rounded-full border border-cyan/25 px-2 py-1 text-[10px]">
                  #{tag}
                </span>
              ))}
            </div>
            <p className="mt-3 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
              verified {recipe.verified_at ? new Date(recipe.verified_at).toISOString() : "pending QA"}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
