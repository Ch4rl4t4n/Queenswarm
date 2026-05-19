"use client";

import { CreditCardIcon, Loader2Icon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { InfoHint } from "@/components/hive/info-hint";
import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson, hivePutJson } from "@/lib/api";
import type { StripeConfigStatus } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

export function StripeCheckoutSettingsPanel(): JSX.Element {
  const { language } = useUiLanguage();
  const sk = language === "sk";

  const [status, setStatus] = useState<StripeConfigStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [secretInput, setSecretInput] = useState("");
  const [webhookInput, setWebhookInput] = useState("");
  const [forbidden, setForbidden] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const payload = await hiveGet<StripeConfigStatus>("billing/stripe-config");
      setStatus(payload);
      setForbidden(false);
    } catch (e) {
      if (e instanceof HiveApiError && e.status === 403) {
        setForbidden(true);
        setStatus(null);
      } else {
        toast.error(e instanceof HiveApiError ? e.message : sk ? "Nepodarilo sa načítať Stripe." : "Could not load Stripe config.");
      }
    } finally {
      setLoading(false);
    }
  }, [sk]);

  useEffect(() => {
    void load();
  }, [load]);

  async function save(): Promise<void> {
    const secret = secretInput.trim();
    const webhook = webhookInput.trim();
    if (!secret && !webhook) {
      toast.error(sk ? "Vlož aspoň jeden Stripe secret." : "Paste at least one Stripe secret.");
      return;
    }
    setBusy(true);
    try {
      const payload = await hivePutJson<StripeConfigStatus>("billing/stripe-config", {
        ...(secret ? { secret_key: secret } : {}),
        ...(webhook ? { webhook_secret: webhook } : {}),
      });
      setStatus(payload);
      setSecretInput("");
      setWebhookInput("");
      toast.success(sk ? "Stripe kľúče uložené do hive vault." : "Stripe keys saved to hive vault.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : sk ? "Uloženie zlyhalo." : "Save failed.");
    } finally {
      setBusy(false);
    }
  }

  async function testConnection(): Promise<void> {
    setBusy(true);
    try {
      const res = await hivePostJson<{ status: string; message: string }>("billing/stripe-config/test", {});
      if (res.status === "ok") {
        toast.success(res.message);
      } else {
        toast.error(res.message);
      }
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : sk ? "Test zlyhal." : "Test failed.");
    } finally {
      setBusy(false);
    }
  }

  async function clearVault(): Promise<void> {
    setBusy(true);
    try {
      const payload = await hivePutJson<StripeConfigStatus>("billing/stripe-config", {
        clear_secret_key: true,
        clear_webhook_secret: true,
      });
      setStatus(payload);
      toast.message(sk ? "Hive vault vyčistený — platí .env fallback." : "Hive vault cleared — .env fallback applies.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : sk ? "Vymazanie zlyhalo." : "Clear failed.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <V4Card>
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden />
          {sk ? "Načítavam Stripe…" : "Loading Stripe…"}
        </p>
      </V4Card>
    );
  }

  if (forbidden) {
    return (
      <V4Card>
        <p className="text-sm text-(--qs-text-3)">
          {sk
            ? "Stripe kľúče môže meniť len admin operátor."
            : "Only an admin operator can manage Stripe keys."}
        </p>
      </V4Card>
    );
  }

  return (
    <V4Card>
      <V4CardHeader
        title={sk ? "Stripe checkout" : "Stripe checkout"}
        description={
          sk
            ? "Premium skill nákupy — kľúče sa ukladajú šifrovane do hive vault (nie do prehliadača)."
            : "Premium skill purchases — keys are encrypted in the hive vault (never stored in the browser)."
        }
        actions={
          <V4Badge tone={status?.checkout_ready ? "ok" : "warn"}>
            {status?.checkout_ready
              ? sk
                ? "checkout pripravený"
                : "checkout ready"
              : sk
                ? "checkout vypnutý"
                : "checkout off"}
          </V4Badge>
        }
      />

      <div className="mb-4 flex items-start gap-2 text-xs text-(--qs-text-3)">
        <CreditCardIcon className="mt-0.5 h-4 w-4 shrink-0 text-pollen" aria-hidden />
        <p>
          {sk
            ? "Odporúčame restricted key (rk_…) s právom Checkout Sessions. Webhook secret nájdeš v Stripe Dashboard → Developers → Webhooks."
            : "Prefer a restricted key (rk_…) with Checkout Sessions permission. Webhook secret lives in Stripe Dashboard → Developers → Webhooks."}
        </p>
        <InfoHint
          title={sk ? "Prečo tu nie env súbor?" : "Why not .env only?"}
          description={
            sk
              ? "Kľúče z UI sa ukladajú do Postgres vault (Fernet). Server env stále funguje ako fallback pre Docker deploy."
              : "UI keys persist in Postgres vault (Fernet). Server env remains a fallback for Docker deploy."
          }
        />
      </div>

      <dl className="mb-5 grid gap-2 text-xs text-(--qs-text-2) sm:grid-cols-2">
        <div>
          <dt className="text-(--qs-text-3)">{sk ? "Secret key" : "Secret key"}</dt>
          <dd className="font-mono">{status?.secret_key_masked ?? (sk ? "— nenastavené" : "— not set")}</dd>
          <dd className="text-(--qs-text-3)">source: {status?.secret_key_source ?? "none"}</dd>
        </div>
        <div>
          <dt className="text-(--qs-text-3)">{sk ? "Webhook secret" : "Webhook secret"}</dt>
          <dd className="font-mono">{status?.webhook_secret_masked ?? (sk ? "— nenastavené" : "— not set")}</dd>
          <dd className="text-(--qs-text-3)">source: {status?.webhook_secret_source ?? "none"}</dd>
        </div>
      </dl>

      <p className="mb-4 break-all text-xs text-(--qs-text-3)">
        Webhook URL:{" "}
        <span className="font-mono text-(--qs-cyan)">{status?.webhook_url ?? "—"}</span>
      </p>

      {status?.env_fallback_active ? (
        <p
          className="mb-4 rounded-xl border border-pollen/35 bg-pollen/10 px-4 py-3 text-sm text-pollen"
          role="status"
        >
          {sk
            ? "Aktívny je fallback z Docker env — vault kľúče majú prioritu po uložení."
            : "Docker env fallback is active — vault keys take priority once saved."}
        </p>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <label className="block qs-label">
          {sk ? "Nový Stripe secret key" : "New Stripe secret key"}
          <input
            type="password"
            autoComplete="off"
            className="v4-input mt-2 w-full font-mono text-sm"
            placeholder="sk_live_… or rk_live_…"
            value={secretInput}
            onChange={(e) => setSecretInput(e.target.value)}
          />
        </label>
        <label className="block qs-label">
          {sk ? "Nový webhook secret" : "New webhook secret"}
          <input
            type="password"
            autoComplete="off"
            className="v4-input mt-2 w-full font-mono text-sm"
            placeholder="whsec_…"
            value={webhookInput}
            onChange={(e) => setWebhookInput(e.target.value)}
          />
        </label>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        <button
          type="button"
          className={cn("qs-btn qs-btn--primary qs-btn--sm", busy && "opacity-60")}
          disabled={busy}
          onClick={() => void save()}
        >
          {busy ? (sk ? "Ukladám…" : "Saving…") : sk ? "Uložiť do vault" : "Save to vault"}
        </button>
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm"
          disabled={busy || !status?.checkout_ready}
          onClick={() => void testConnection()}
        >
          {sk ? "Otestovať Stripe" : "Test Stripe"}
        </button>
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm text-(--qs-red)"
          disabled={busy}
          onClick={() => void clearVault()}
        >
          {sk ? "Vymazať vault" : "Clear vault"}
        </button>
      </div>
    </V4Card>
  );
}
