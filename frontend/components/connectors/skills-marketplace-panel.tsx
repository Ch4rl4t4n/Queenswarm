"use client";

import { CopyIcon, CreditCardIcon, DownloadIcon, Loader2Icon, SparklesIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { VerifiedPollenLeaderboard } from "@/components/hive/verified-pollen-leaderboard";
import { V4Badge, V4CardHeader, V4Chip } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type {
  SkillCatalogRecipeItem,
  SkillCatalogResponse,
  SkillCheckoutResponse,
  SkillConfirmCheckoutResponse,
  SkillExportResponse,
  SkillUnlockStatusResponse,
} from "@/lib/hive-types";
import { downloadSkillExportBundle } from "@/lib/skill-export-utils";
import { cn } from "@/lib/utils";

/** Skills marketplace — built-in hive skills + verified recipe exports. */
export function SkillsMarketplacePanel({
  checkoutSessionId,
  purchaseOutcome,
}: {
  checkoutSessionId?: string | null;
  purchaseOutcome?: "success" | "cancel" | null;
}): JSX.Element {
  const [catalog, setCatalog] = useState<SkillCatalogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [exportBusyId, setExportBusyId] = useState<string | null>(null);
  const [preview, setPreview] = useState<SkillExportResponse | null>(null);
  const [unlocks, setUnlocks] = useState<SkillUnlockStatusResponse | null>(null);
  const [checkoutBusyId, setCheckoutBusyId] = useState<string | null>(null);

  const loadCatalog = useCallback(async () => {
    setLoading(true);
    try {
      const [payload, unlockPayload] = await Promise.all([
        hiveGet<SkillCatalogResponse>("recipes/skills-catalog?limit=80"),
        hiveGet<SkillUnlockStatusResponse>("recipes/skills/unlocks").catch(() => null),
      ]);
      setCatalog(payload);
      setUnlocks(unlockPayload);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Skills catalog unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCatalog();
  }, [loadCatalog]);

  useEffect(() => {
    if (purchaseOutcome === "cancel") {
      toast.message("Checkout cancelled — no charge applied.");
      return;
    }
    if (purchaseOutcome !== "success" || !checkoutSessionId) {
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const confirmed = await hivePostJson<SkillConfirmCheckoutResponse>("recipes/skills/confirm-checkout", {
          checkout_session_id: checkoutSessionId,
        });
        if (cancelled) return;
        if (confirmed.status === "unlocked") {
          toast.success("Skill unlocked!", {
            description: confirmed.message ?? "You can export premium skills now.",
          });
          await loadCatalog();
          return;
        }
        toast.message(confirmed.message ?? "Payment still processing…");
      } catch (e) {
        if (!cancelled) {
          toast.error(e instanceof HiveApiError ? e.message : "Could not confirm checkout.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [checkoutSessionId, loadCatalog, purchaseOutcome]);

  const exportRecipe = useCallback(async (recipe: SkillCatalogRecipeItem) => {
    setExportBusyId(recipe.id);
    try {
      const bundle = await hivePostJson<SkillExportResponse>(`recipes/${recipe.id}/export-skill`, {});
      setPreview(bundle);
      await downloadSkillExportBundle(bundle);
      toast.success(`Exported ${bundle.meta.slug}`, {
        description: "SKILL.md + HIVE.md + tasks.prompt.md downloaded.",
      });
    } catch (e) {
      if (e instanceof HiveApiError && e.status === 402) {
        toast.error("Premium skill — purchase required.", {
          description: recipe.premium
            ? `Unlock for €${((recipe.price_eur_cents ?? 0) / 100).toFixed(2)} or upgrade to Pro.`
            : "Upgrade to Pro or purchase this skill.",
        });
      } else {
        toast.error(e instanceof HiveApiError ? e.message : "Export failed.");
      }
    } finally {
      setExportBusyId(null);
    }
  }, []);

  const purchaseRecipe = useCallback(
    async (recipe: SkillCatalogRecipeItem) => {
      setCheckoutBusyId(recipe.id);
      try {
        const checkout = await hivePostJson<SkillCheckoutResponse>("recipes/skills/checkout", {
          recipe_id: recipe.id,
        });
        if (checkout.status === "already_unlocked") {
          toast.success("Already unlocked — export now.");
          await exportRecipe(recipe);
          return;
        }
        if (checkout.checkout_url) {
          window.location.href = checkout.checkout_url;
          return;
        }
        toast.error("Checkout URL missing — configure Stripe keys.");
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Checkout failed.");
      } finally {
        setCheckoutBusyId(null);
      }
    },
    [exportRecipe],
  );

  const handleRecipeAction = useCallback(
    (recipe: SkillCatalogRecipeItem) => {
      if (recipe.premium && !recipe.unlocked) {
        void purchaseRecipe(recipe);
        return;
      }
      void exportRecipe(recipe);
    },
    [exportRecipe, purchaseRecipe],
  );

  const copyInstall = useCallback(async () => {
    if (!preview) return;
    try {
      await navigator.clipboard.writeText(preview.install_command);
      toast.success("Install command copied.");
    } catch {
      toast.error("Clipboard unavailable.");
    }
  }, [preview]);

  return (
    <div className="space-y-5">
      <VerifiedPollenLeaderboard limit={8} compact />

      {unlocks ? (
        <p className="text-xs text-(--qs-text-3)">
          Stripe checkout: {unlocks.stripe_checkout_ready ? "ready" : "not configured"} · default premium €
          {(unlocks.premium_price_eur_cents_default / 100).toFixed(2)}
        </p>
      ) : null}

      {err ? (
        <p className="rounded-xl border border-(--qs-red)/35 bg-(--qs-red)/10 px-4 py-3 text-sm text-(--qs-red)">
          {err}
        </p>
      ) : null}

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading skills catalog…
        </p>
      ) : null}

      <section>
        <V4CardHeader
          as="h3"
          title="Built-in hive skills"
          description="Supervisor SkillLibrary — grill-me, TDD, diagnose, and more."
        />
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {(catalog?.builtin ?? []).map((skill) => (
            <article key={skill.slug} className="v4-int-card">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="v4-int-name">{skill.title}</p>
                  <p className="v4-int-meta font-mono text-xs">{skill.slug} · v{skill.version}</p>
                </div>
                <V4Badge tone="info">builtin</V4Badge>
              </div>
              {(skill.keywords ?? []).length ? (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {skill.keywords.slice(0, 4).map((kw) => (
                    <V4Chip key={kw} type="span">
                      {kw}
                    </V4Chip>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </section>

      <section>
        <V4CardHeader
          as="h3"
          title="Verified recipe skills"
          description="Export Recipe Library rows as Cursor/Claude-compatible bundles with simulation audit metadata."
        />
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
          {(catalog?.recipes ?? []).map((recipe) => (
            <article key={recipe.id} className="v4-int-card flex flex-col gap-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="v4-int-name truncate">{recipe.name}</p>
                  <p className="v4-int-meta">
                    {recipe.slug} · ★ {(recipe.success_rate * 100).toFixed(0)}% · pollen{" "}
                    {Math.round(recipe.avg_pollen_earned)}
                  </p>
                </div>
                <V4Badge tone={recipe.premium && !recipe.unlocked ? "warn" : "ok"}>
                  {recipe.premium && !recipe.unlocked ? "premium" : "verified"}
                </V4Badge>
              </div>
              {recipe.premium && !recipe.unlocked ? (
                <p className="text-xs text-pollen">
                  €{((recipe.price_eur_cents ?? 0) / 100).toFixed(2)} one-time unlock
                </p>
              ) : null}
              {recipe.description ? (
                <p className="line-clamp-2 text-xs text-(--qs-text-3)">{recipe.description}</p>
              ) : null}
              <button
                type="button"
                className={cn("qs-btn qs-btn--primary qs-btn--sm w-fit")}
                disabled={exportBusyId === recipe.id || checkoutBusyId === recipe.id}
                onClick={() => handleRecipeAction(recipe)}
              >
                {exportBusyId === recipe.id || checkoutBusyId === recipe.id ? (
                  <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden />
                ) : recipe.premium && !recipe.unlocked ? (
                  <CreditCardIcon className="h-3.5 w-3.5" aria-hidden />
                ) : (
                  <DownloadIcon className="h-3.5 w-3.5" aria-hidden />
                )}
                {recipe.premium && !recipe.unlocked ? "Unlock & export" : "Export skill"}
              </button>
            </article>
          ))}
          {!loading && !(catalog?.recipes ?? []).length ? (
            <p className="text-sm text-(--qs-text-3)">No verified recipes yet — run missions and promote workflows.</p>
          ) : null}
        </div>
      </section>

      {preview ? (
        <section className="v4-learning-panel space-y-3 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <SparklesIcon className="h-4 w-4 text-pollen" aria-hidden />
              <p className="text-sm font-medium text-(--qs-text)">Last export: {preview.meta.slug}</p>
            </div>
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void copyInstall()}>
              <CopyIcon className="h-3.5 w-3.5" aria-hidden /> Copy install cmd
            </button>
          </div>
          <p className="font-mono text-xs text-cyan">{preview.install_command}</p>
          <p className="text-xs text-(--qs-text-3)">{preview.install_hint}</p>
          <pre className="max-h-48 overflow-auto rounded-lg border border-(--qs-border) bg-black/40 p-3 font-mono text-[11px] text-(--qs-text-2)">
            {preview.files.find((f) => f.path.endsWith("SKILL.md"))?.content.slice(0, 1200) ?? ""}
          </pre>
        </section>
      ) : null}
    </div>
  );
}
