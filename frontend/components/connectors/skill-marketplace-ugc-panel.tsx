"use client";

import { Loader2Icon, SendIcon, ShieldCheckIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4CardHeader, V4Chip } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type {
  RecipeRow,
  SkillMarketplaceConfigPayload,
  SkillMarketplaceListingRow,
} from "@/lib/hive-types";
import { cn } from "@/lib/utils";

function formatEur(cents: number): string {
  return `€${(cents / 100).toFixed(2)}`;
}

function listingTone(status: string): "ok" | "warn" | "info" | "err" {
  if (status === "approved") return "ok";
  if (status === "pending_review") return "warn";
  if (status === "rejected") return "err";
  return "info";
}

interface SkillMarketplaceUgcPanelProps {
  readonly isCurator?: boolean;
}

/** Submit verified recipes for curator review — Phase 1 UGC marketplace. */
export function SkillMarketplaceUgcPanel({ isCurator = false }: SkillMarketplaceUgcPanelProps): JSX.Element | null {
  const [config, setConfig] = useState<SkillMarketplaceConfigPayload | null>(null);
  const [listings, setListings] = useState<SkillMarketplaceListingRow[]>([]);
  const [curatorQueue, setCuratorQueue] = useState<SkillMarketplaceListingRow[]>([]);
  const [recipes, setRecipes] = useState<RecipeRow[]>([]);
  const [recipeId, setRecipeId] = useState("");
  const [priceCents, setPriceCents] = useState(1900);
  const [pitch, setPitch] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [cfg, mine, catalog] = await Promise.all([
        hiveGet<SkillMarketplaceConfigPayload>("recipes/marketplace/config"),
        hiveGet<SkillMarketplaceListingRow[]>("recipes/marketplace/my-listings"),
        hiveGet<RecipeRow[]>("recipes?verified_only=true&limit=80"),
      ]);
      setConfig(cfg);
      setListings(mine);
      setRecipes(catalog);
      if (isCurator) {
        const queue = await hiveGet<SkillMarketplaceListingRow[]>("recipes/marketplace/curator-queue");
        setCuratorQueue(queue);
      }
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "UGC marketplace unavailable.");
    } finally {
      setLoading(false);
    }
  }, [isCurator]);

  useEffect(() => {
    void load();
  }, [load]);

  const eligibleRecipes = useMemo(() => {
    const blocked = new Set(
      listings.filter((row) => row.status === "pending_review" || row.status === "approved").map((row) => row.recipe_id),
    );
    return recipes.filter((r) => !blocked.has(r.id));
  }, [listings, recipes]);

  const submitListing = useCallback(async () => {
    if (!recipeId) {
      toast.message("Pick a verified recipe.");
      return;
    }
    setBusy(true);
    try {
      await hivePostJson<SkillMarketplaceListingRow>("recipes/marketplace/submit", {
        recipe_id: recipeId,
        price_eur_cents: priceCents,
        pitch: pitch.trim() || null,
      });
      toast.success("Submitted for curator review.");
      setPitch("");
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Submit failed.");
    } finally {
      setBusy(false);
    }
  }, [load, pitch, priceCents, recipeId]);

  const reviewListing = useCallback(
    async (listingId: string, action: "approve" | "reject") => {
      setBusy(true);
      try {
        await hivePostJson<SkillMarketplaceListingRow>(`recipes/marketplace/listings/${listingId}/review`, {
          action,
          curator_note: action === "reject" ? "Needs more verification detail." : null,
        });
        toast.success(action === "approve" ? "Listing approved." : "Listing rejected.");
        await load();
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Review failed.");
      } finally {
        setBusy(false);
      }
    },
    [load],
  );

  if (loading) {
    return (
      <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
        <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading UGC marketplace…
      </p>
    );
  }

  if (!config?.enabled) {
    return null;
  }

  return (
    <section className="rounded-2xl border border-(--qs-green)/30 bg-(--qs-green)/5 p-4 md:p-5">
      <V4CardHeader
        as="h3"
        title="Publish your verified skill (UGC)"
        description={`Curator review · platform keeps ${config.platform_cut_display} on each sale`}
      />

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="space-y-3">
          <label className="block text-xs text-(--qs-text-3)">
            Verified recipe
            <select
              value={recipeId}
              onChange={(e) => setRecipeId(e.target.value)}
              className="qs-input mt-1 w-full"
              disabled={busy}
            >
              <option value="">Select recipe…</option>
              {eligibleRecipes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </label>

          <div>
            <p className="text-xs text-(--qs-text-3)">Price tier</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {config.price_tiers_cents.map((tier) => (
                <V4Chip key={tier} active={priceCents === tier} onClick={() => setPriceCents(tier)}>
                  {formatEur(tier)}
                </V4Chip>
              ))}
            </div>
          </div>

          <label className="block text-xs text-(--qs-text-3)">
            Pitch (optional)
            <textarea
              value={pitch}
              onChange={(e) => setPitch(e.target.value)}
              rows={3}
              className="qs-input mt-1 w-full resize-y"
              placeholder="Who is this for? What outcome does the buyer get?"
              disabled={busy}
            />
          </label>

          <button type="button" className="qs-btn qs-btn--primary qs-btn--sm gap-2" disabled={busy} onClick={() => void submitListing()}>
            {busy ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : <SendIcon className="h-4 w-4" aria-hidden />}
            Submit for review
          </button>
        </div>

        <div>
          <p className="text-xs font-medium text-(--qs-text-2)">Your submissions</p>
          <ul className="mt-2 space-y-2">
            {listings.map((row) => (
              <li key={row.id} className="rounded-xl border border-(--qs-border) bg-black/30 px-3 py-2 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-(--qs-text)">{row.recipe_name}</span>
                  <V4Badge tone={listingTone(row.status)}>{row.status.replace("_", " ")}</V4Badge>
                </div>
                <p className="mt-1 text-(--qs-text-3)">
                  {formatEur(row.price_eur_cents)} · you keep {formatEur(row.price_eur_cents - Math.round((row.price_eur_cents * row.platform_cut_bps) / 10_000))}
                </p>
                {row.curator_note ? <p className="mt-1 text-(--qs-magenta)">{row.curator_note}</p> : null}
              </li>
            ))}
            {!listings.length ? <p className="text-xs text-(--qs-text-3)">No submissions yet.</p> : null}
          </ul>
        </div>
      </div>

      {isCurator ? (
        <div className="mt-6 border-t border-(--qs-border) pt-4">
          <div className="mb-2 flex items-center gap-2">
            <ShieldCheckIcon className="h-4 w-4 text-cyan" aria-hidden />
            <p className="text-sm font-medium text-(--qs-text)">Curator queue</p>
          </div>
          <ul className="space-y-2">
            {curatorQueue.map((row) => (
              <li key={row.id} className={cn("rounded-xl border border-cyan/25 bg-cyan/5 px-3 py-3 text-xs")}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-(--qs-text)">{row.recipe_name}</span>
                  <span className="text-pollen">{formatEur(row.price_eur_cents)}</span>
                </div>
                {row.pitch ? <p className="mt-1 text-(--qs-text-3)">{row.pitch}</p> : null}
                <div className="mt-2 flex flex-wrap gap-2">
                  <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" disabled={busy} onClick={() => void reviewListing(row.id, "approve")}>
                    Approve
                  </button>
                  <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" disabled={busy} onClick={() => void reviewListing(row.id, "reject")}>
                    Reject
                  </button>
                </div>
              </li>
            ))}
            {!curatorQueue.length ? <p className="text-xs text-(--qs-text-3)">Queue empty — no pending listings.</p> : null}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
