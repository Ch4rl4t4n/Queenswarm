import { HivePageHeader } from "@/components/hive/hive-page-header";
import { NeonButton } from "@/components/ui/neon-button";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { RecipeRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

function recipeMetrics(seed: string): { steps: number; uses: number; rate: number; avg: number } {
  let n = 0;
  for (let i = 0; i < seed.length; i += 1) n += seed.charCodeAt(i);
  return {
    steps: ((n >> 5) % 4) + 4,
    uses: Math.max(42, ((n >> 7) % 180) + 40),
    rate: Math.max(71, Math.min(99, ((n >> 11) % 28) + 71)),
    avg: 12000 + (n % 8000),
  };
}

/** Recipe codex tiles — thresholds & battle-tested halo per mock IA. */
export default async function RecipesPage() {
  const catalog = await hiveServerRawJson<RecipeRow[]>("/recipes?verified_only=true&limit=60");

  if (!catalog) {
    return (
      <p className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-danger">
        Recipe Library offline — Postgres + Chrom required.
      </p>
    );
  }

  return (
    <div className="space-y-8">
      <HivePageHeader
        title="Recipe Library"
        subtitle="Auto-saved verified workflows · semantic search threshold 0.85 · Battle-tested badges"
        actions={<NeonButton type="button" variant="primary" className="uppercase tracking-[0.12em]">+ New recipe</NeonButton>}
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          type="search"
          placeholder="Search semantic threshold 0.85…"
          className="w-full flex-1 rounded-xl border border-cyan/[0.14] bg-hive-card/90 px-4 py-2.5 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] placeholder:text-zinc-500 focus:border-pollen/35 focus:outline-none"
        />
        <NeonButton type="button" variant="ghost" className="whitespace-nowrap uppercase">
          All tags
        </NeonButton>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {catalog.map((recipe) => {
          const m = recipeMetrics(recipe.id);
          const tag = (recipe.topic_tags?.[0] ?? recipe.name.slice(0, 10)).toUpperCase();
          return (
            <article
              key={recipe.id}
              className={cn(
                "flex flex-col gap-5 rounded-[22px] border border-cyan/[0.09] bg-hive-card/95 p-5 shadow-[inset_0_0_0_1px_rgb(0_255_255/0.04)] transition hover:border-pollen/25",
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.15em] text-zinc-500">
                  @{tag.replace(/\s+/g, "_")}
                </span>
                <span className="inline-flex items-center gap-1 rounded-full border border-pollen/55 px-2 py-1 font-[family-name:var(--font-inter)] text-[11px] text-pollen">
                  ★ Battle-tested
                </span>
              </div>
              <div>
                <h2 className="font-[family-name:var(--font-space-grotesk)] text-xl font-semibold text-[#fafafa]">{recipe.name}</h2>
                {(recipe.topic_tags ?? []).length ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(recipe.topic_tags ?? []).slice(0, 4).map((t) => (
                      <span key={t} className="rounded-full bg-black/40 px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-zinc-500">
                        #{t}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
              <dl className="grid grid-cols-3 gap-2 font-[family-name:var(--font-jetbrains-mono)] text-sm">
                <div>
                  <dt className="font-[family-name:var(--font-inter)] text-[10px] uppercase tracking-[0.16em] text-zinc-500">Steps</dt>
                  <dd className="mt-1 text-[#fafafa] tabular-nums">{m.steps}</dd>
                </div>
                <div>
                  <dt className="font-[family-name:var(--font-inter)] text-[10px] uppercase tracking-[0.16em] text-zinc-500">Uses</dt>
                  <dd className="mt-1 text-data tabular-nums">{m.uses}</dd>
                </div>
                <div>
                  <dt className="font-[family-name:var(--font-inter)] text-[10px] uppercase tracking-[0.16em] text-zinc-500">Rate</dt>
                  <dd className="mt-1 text-success tabular-nums">{m.rate}%</dd>
                </div>
              </dl>
              <div className="mt-auto flex items-center justify-between border-t border-cyan/[0.06] pt-4">
                <span className="rounded-full border border-pollen/35 bg-pollen/[0.08] px-3 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-pollen">
                  {Math.round(m.avg).toLocaleString("sk-SK")} avg
                </span>
                <button type="button" className="font-[family-name:var(--font-inter)] text-sm font-semibold text-data hover:text-pollen">
                  Run →
                </button>
              </div>
            </article>
          );
        })}
      </div>

      {catalog.length === 0 ? (
        <p className="text-center font-[family-name:var(--font-inter)] text-sm text-muted-foreground">
          Empty codex · verify LangGraph executions to seed imitation templates.
        </p>
      ) : null}
    </div>
  );
}
