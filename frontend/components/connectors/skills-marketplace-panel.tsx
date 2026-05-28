"use client";

import { CopyIcon, CreditCardIcon, DownloadIcon, Loader2Icon, RocketIcon, SparklesIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { usePlatform } from "@/components/hive/platform-context";
import { SkillMarketplaceUgcPanel } from "@/components/connectors/skill-marketplace-ugc-panel";
import { SkillProductPublishPanel } from "@/components/connectors/skill-product-publish-panel";
import { V4Badge, V4CardHeader, V4Chip } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type {
  SkillCatalogRecipeItem,
  SkillCatalogResponse,
  SkillExportResponse,
  SkillUnlockStatusResponse,
} from "@/lib/hive-types";
import { startProductMission } from "@/lib/product-mission";
import { downloadSkillExportBundle } from "@/lib/skill-export-utils";
import { cn } from "@/lib/utils";

/** Skills marketplace — built-in hive skills + verified recipe exports. */
export function SkillsMarketplacePanel(): JSX.Element {
  const { hasFeature, isAdmin } = usePlatform();
  const showFactory = hasFeature("skills_export_factory");
  const showProductMission = hasFeature("product_mission");
  const showUgc = hasFeature("skills_marketplace");
  const [catalog, setCatalog] = useState<SkillCatalogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [exportBusyId, setExportBusyId] = useState<string | null>(null);
  const [preview, setPreview] = useState<SkillExportResponse | null>(null);
  const [unlocks, setUnlocks] = useState<SkillUnlockStatusResponse | null>(null);
  const checkoutBusyId: string | null = null;
  const [missionBusy, setMissionBusy] = useState(false);
  const [nicheHint, setNicheHint] = useState("");

  const checkoutAvailable = false;
  const recipeRows = useMemo(() => catalog?.recipes ?? [], [catalog?.recipes]);
  const sortByPrice = useCallback(
    (a: SkillCatalogRecipeItem, b: SkillCatalogRecipeItem) =>
      (a.price_eur_cents ?? 0) - (b.price_eur_cents ?? 0),
    [],
  );
  const premiumLocked = useMemo(
    () => recipeRows.filter((row) => row.premium && !row.unlocked).sort(sortByPrice),
    [recipeRows, sortByPrice],
  );
  const premiumUnlocked = useMemo(
    () => recipeRows.filter((row) => row.premium && row.unlocked).sort(sortByPrice),
    [recipeRows, sortByPrice],
  );
  const freeVerified = recipeRows.filter((row) => !row.premium);
  const hasLockedPremium = premiumLocked.length > 0;
  const minPremiumEur =
    premiumLocked.length > 0
      ? (premiumLocked[0]?.price_eur_cents ?? 0) / 100
      : (unlocks?.premium_price_eur_cents_default ?? 0) / 100;

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

  const handleRecipeAction = useCallback(
    (recipe: SkillCatalogRecipeItem) => {
      if (recipe.premium && !recipe.unlocked && !checkoutAvailable) {
        toast.error("Premium checkout has been removed.", {
          description: "Premium skill unlock via in-app checkout is no longer available.",
        });
        return;
      }
      void exportRecipe(recipe);
    },
    [checkoutAvailable, exportRecipe],
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

  const handleStartProductMission = useCallback(async () => {
    setMissionBusy(true);
    try {
      toast.message("Otváram Ballroom — misia sa spustí v chate…");
      await startProductMission({ nicheHint: nicheHint.trim() || undefined });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Product mission failed.";
      toast.error(msg);
      setMissionBusy(false);
    }
  }, [nicheHint]);

  return (
    <div className="space-y-5">
      {showFactory && showProductMission ? (
      <section className="rounded-2xl border border-cyan/30 bg-cyan/5 p-4 md:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <RocketIcon className="h-4 w-4 text-cyan" aria-hidden />
              <p className="text-sm font-medium text-(--qs-text)">Revenue swarm factory</p>
            </div>
            <p className="max-w-2xl text-xs text-(--qs-text-3)">
              Swarm produces verified skills, plugins, and addons → export bundle → sell on{" "}
              <strong className="text-(--qs-text-2)">GitHub</strong>,{" "}
              <strong className="text-(--qs-text-2)">Gumroad</strong>, and external channels. Spustí sa 5-kroková misia v
              Ballroom — nie len prázdny chat.
            </p>
            <label className="mt-3 block max-w-md text-xs text-(--qs-text-3)">
              Niche (voliteľné)
              <input
                type="text"
                value={nicheHint}
                onChange={(e) => setNicheHint(e.target.value)}
                placeholder="newsletter growth, crypto alerts, SEO blog…"
                className="mt-1 w-full rounded-lg border border-(--qs-border) bg-black/40 px-3 py-2 text-sm text-(--qs-text) placeholder:text-(--qs-text-3)"
                disabled={missionBusy}
              />
            </label>
          </div>
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm gap-2"
            disabled={missionBusy}
            onClick={() => void handleStartProductMission()}
          >
            {missionBusy ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : null}
            {missionBusy ? "Spúšťam misiu…" : "Start product mission"}
          </button>
        </div>
      </section>
      ) : null}

      {showUgc ? <SkillMarketplaceUgcPanel isCurator={isAdmin} /> : null}

      <section className="rounded-2xl border border-pollen/30 bg-pollen/5 p-4 md:p-5">
        <V4CardHeader
          as="h3"
          title="Premium skills"
          description="In-app premium checkout is removed; free verified exports remain available."
        />
        {unlocks ? (
          <p className="mt-2 text-xs text-(--qs-text-3)">
            Premium checkout:{" "}
            <span className={checkoutAvailable ? "text-(--qs-green)" : "text-(--qs-red)"}>
              {checkoutAvailable ? "ready" : "removed"}
            </span>
            {hasLockedPremium ? (
              <>
                {" "}
                · premium od{" "}
                <span className="font-medium text-pollen">€{minPremiumEur.toFixed(2)}</span>
                {premiumLocked.length > 1 ? (
                  <span>
                    {" "}
                    (€9 / €19 / €29 podľa skillu)
                  </span>
                ) : null}
              </>
            ) : null}
          </p>
        ) : null}

        {!checkoutAvailable && hasLockedPremium ? (
          <p
            className="mt-3 rounded-xl border border-pollen/35 bg-pollen/10 px-4 py-3 text-sm text-pollen"
            role="status"
          >
            Premium in-app checkout has been removed.
          </p>
        ) : null}

        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {premiumLocked.map((recipe) => (
            <RecipeSkillCard
              key={recipe.id}
              recipe={recipe}
              checkoutAvailable={checkoutAvailable}
              exportBusyId={exportBusyId}
              checkoutBusyId={checkoutBusyId}
              onAction={handleRecipeAction}
              emphasizePremium
            />
          ))}
          {premiumUnlocked.map((recipe) => (
            <RecipeSkillCard
              key={recipe.id}
              recipe={recipe}
              checkoutAvailable={checkoutAvailable}
              exportBusyId={exportBusyId}
              checkoutBusyId={checkoutBusyId}
              onAction={handleRecipeAction}
            />
          ))}
          {!loading && !premiumLocked.length && !premiumUnlocked.length ? (
            <p className="text-sm text-(--qs-text-3) md:col-span-2 xl:col-span-3">
              {checkoutAvailable
                ? "Premium catalog is loading — refresh in a moment. Verified premium recipes appear here with Unlock & export buttons."
                : "Premium in-app unlock is disabled. Built-in hive skills below remain free."}
            </p>
          ) : null}
        </div>
      </section>

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
          title="Free verified recipe skills"
          description="Already unlocked verified workflows — export without purchase."
        />
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
          {freeVerified.map((recipe) => (
            <RecipeSkillCard
              key={recipe.id}
              recipe={recipe}
              checkoutAvailable={checkoutAvailable}
              exportBusyId={exportBusyId}
              checkoutBusyId={checkoutBusyId}
              onAction={handleRecipeAction}
            />
          ))}
          {!loading && !freeVerified.length ? (
            <p className="text-sm text-(--qs-text-3)">
              No free verified recipes yet — run missions in Ballroom and promote workflows to the Recipe Library.
            </p>
          ) : null}
        </div>
      </section>

      {preview && showFactory ? (
        <>
          <SkillProductPublishPanel bundle={preview} />
          <section className="v4-learning-panel space-y-3 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <SparklesIcon className="h-4 w-4 text-pollen" aria-hidden />
                <p className="text-sm font-medium text-(--qs-text)">Bundle preview: {preview.meta.slug}</p>
              </div>
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void copyInstall()}>
                <CopyIcon className="h-3.5 w-3.5" aria-hidden /> Copy install cmd
              </button>
            </div>
            <p className="font-mono text-xs text-cyan">{preview.install_command}</p>
            <pre className="max-h-48 overflow-auto rounded-lg border border-(--qs-border) bg-black/40 p-3 font-mono text-[11px] text-(--qs-text-2)">
              {preview.files.find((f) => f.path.endsWith("SKILL.md"))?.content.slice(0, 1200) ?? ""}
            </pre>
          </section>
        </>
      ) : null}
    </div>
  );
}

function RecipeSkillCard({
  recipe,
  checkoutAvailable,
  exportBusyId,
  checkoutBusyId,
  onAction,
  emphasizePremium = false,
}: {
  recipe: SkillCatalogRecipeItem;
  checkoutAvailable: boolean;
  exportBusyId: string | null;
  checkoutBusyId: string | null;
  onAction: (recipe: SkillCatalogRecipeItem) => void;
  emphasizePremium?: boolean;
}): JSX.Element {
  const lockedPremium = recipe.premium && !recipe.unlocked;
  const busy = exportBusyId === recipe.id || checkoutBusyId === recipe.id;
  const isStarterTier = lockedPremium && (recipe.price_eur_cents ?? 0) <= 900;

  return (
    <article
      className={cn(
        "v4-int-card flex flex-col gap-3",
        emphasizePremium &&
          lockedPremium &&
          (isStarterTier
            ? "ring-2 ring-(--qs-green)/50 shadow-[0_0_28px_rgba(0,255,136,0.15)]"
            : "ring-1 ring-pollen/40 shadow-[0_0_24px_rgba(255,184,0,0.12)]"),
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="v4-int-name truncate">{recipe.name}</p>
          <p className="v4-int-meta">
            {recipe.slug} · ★ {(recipe.success_rate * 100).toFixed(0)}% · pollen{" "}
            {Math.round(recipe.avg_pollen_earned)}
          </p>
        </div>
        <V4Badge tone={isStarterTier ? "ok" : lockedPremium ? "warn" : recipe.premium ? "ok" : "info"}>
          {recipe.ugc ? "UGC" : isStarterTier ? "starter €9" : lockedPremium ? "premium" : recipe.premium ? "unlocked" : "verified"}
        </V4Badge>
      </div>
      {lockedPremium ? (
        <p className={cn("text-sm font-medium", isStarterTier ? "text-(--qs-green)" : "text-pollen")}>
          €{((recipe.price_eur_cents ?? 0) / 100).toFixed(2)} one-time unlock
          {recipe.ugc && recipe.platform_cut_bps ? (
            <span className="text-xs text-(--qs-text-3)"> · community skill</span>
          ) : null}
          {isStarterTier ? " · najlacnejší vstup" : ""}
        </p>
      ) : null}
      {recipe.description ? (
        <p className="line-clamp-3 text-xs text-(--qs-text-3)">{recipe.description}</p>
      ) : null}
      <div className="v4-dream-cycle-card-actions">
        <button
          type="button"
          className={cn(
            "qs-btn qs-btn--sm",
            lockedPremium && checkoutAvailable ? "qs-btn--primary" : lockedPremium ? "qs-btn--ghost opacity-70" : "qs-btn--primary",
          )}
          disabled={busy || (lockedPremium && !checkoutAvailable)}
          title={lockedPremium && !checkoutAvailable ? "Premium checkout removed on this server" : undefined}
          onClick={() => onAction(recipe)}
        >
          {busy ? (
            <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden />
          ) : lockedPremium ? (
            <CreditCardIcon className="h-3.5 w-3.5" aria-hidden />
          ) : (
            <DownloadIcon className="h-3.5 w-3.5" aria-hidden />
          )}
          {lockedPremium ? (checkoutAvailable ? "Unlock & export" : "Checkout removed") : "Export skill"}
        </button>
      </div>
    </article>
  );
}
