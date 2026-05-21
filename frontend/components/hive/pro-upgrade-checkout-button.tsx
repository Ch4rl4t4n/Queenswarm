"use client";

import { useCallback, useState } from "react";
import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

interface ProUpgradeCheckoutButtonProps {
  className?: string;
  /** When false, button is disabled with operator hint. */
  checkoutReady?: boolean;
  /** Hide when tenant is already Pro/Enterprise. */
  currentTier?: string;
  /** Price label, e.g. "€29/mo". */
  priceLabel?: string;
  size?: "sm" | "md";
}

function fmtEurMonthly(cents: number): string {
  const euros = cents / 100;
  return new Intl.NumberFormat("en-EU", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(euros);
}

/** Starts Stripe Pro subscription checkout and redirects to hosted page. */
export function ProUpgradeCheckoutButton({
  className,
  checkoutReady = false,
  currentTier = "free",
  priceLabel,
  size = "md",
}: ProUpgradeCheckoutButtonProps): JSX.Element | null {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const tier = currentTier.trim().toLowerCase();
  const isAlreadyPro = tier === "pro" || tier === "enterprise";

  const onUpgrade = useCallback(async () => {
    if (!checkoutReady) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/proxy/billing/pro-checkout", { method: "POST" });
      const json = (await res.json().catch(() => ({}))) as {
        detail?: string;
        status?: string;
        checkout_url?: string;
        message?: string;
      };
      if (!res.ok) {
        throw new Error(json.detail ?? "Could not start Pro checkout.");
      }
      if (json.status === "already_pro") {
        window.location.reload();
        return;
      }
      if (json.checkout_url) {
        window.location.href = json.checkout_url;
        return;
      }
      throw new Error(json.message ?? "Stripe did not return a checkout URL.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed.");
    } finally {
      setLoading(false);
    }
  }, [checkoutReady]);

  if (isAlreadyPro) {
    return null;
  }

  const label = priceLabel ?? fmtEurMonthly(2900);

  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <button
        type="button"
        className={cn(
          "qs-btn qs-btn--primary inline-flex items-center justify-center gap-2",
          size === "sm" ? "qs-btn--sm" : "",
        )}
        disabled={!checkoutReady || loading}
        onClick={() => {
          void onUpgrade();
        }}
      >
        {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
        {checkoutReady ? `Upgrade to Pro · ${label}` : "Pro checkout — Stripe keys required"}
      </button>
      {!checkoutReady ? (
        <p className="text-xs text-(--qs-text-3)">
          Operator: set STRIPE_SECRET_KEY and STRIPE_PRO_PRICE_ID in server env, then redeploy.
        </p>
      ) : null}
      {error ? <p className="text-xs text-(--qs-red)">{error}</p> : null}
    </div>
  );
}
