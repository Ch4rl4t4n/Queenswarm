"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveSwitch } from "@/components/ui/hive-switch";
import { NeonButton } from "@/components/ui/neon-button";
import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import type { DashboardOperatorMe, TotpProvisionResponse } from "@/lib/hive-dashboard-session";

export default function SettingsSecurityPage() {
  const [me, setMe] = useState<DashboardOperatorMe | null>(null);
  const [provisionPwd, setProvisionPwd] = useState("");
  const [provisionOut, setProvisionOut] = useState<TotpProvisionResponse | null>(null);
  const [confirmCode, setConfirmCode] = useState("");
  const [disablePwd, setDisablePwd] = useState("");
  const [auditDigest, setAuditDigest] = useState(true);

  const reload = useCallback(async () => {
    try {
      const row = await hiveGet<DashboardOperatorMe>("auth/me");
      setMe(row);
      if (typeof row.notification_prefs?.audit_digest === "boolean") {
        setAuditDigest(row.notification_prefs.audit_digest);
      }
    } catch {
      setMe(null);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function toggleAudit(enabled: boolean): Promise<void> {
    try {
      const next = await hivePatchJson<DashboardOperatorMe>("auth/me/notifications", { audit_digest: enabled });
      setMe(next);
      setAuditDigest(!!next.notification_prefs?.audit_digest);
      toast.success("Audit preference saved");
    } catch (e) {
      if (e instanceof HiveApiError) toast.error(e.message);
      else toast.error("Nepodarilo sa uložiť audit.");
    }
  }

  async function runProvision(): Promise<void> {
    if (!provisionPwd.trim()) {
      toast.error("Zadaj heslo.");
      return;
    }
    try {
      const res = await hivePostJson<TotpProvisionResponse>("auth/profile/totp/provision", {
        password: provisionPwd,
      });
      setProvisionOut(res);
      toast.success("Nový seed vygenerovaný — naskenuj QR.");
      setProvisionPwd("");
      await reload();
    } catch (e) {
      if (e instanceof HiveApiError) toast.error(e.message);
      else toast.error("Provisioning zlyhal.");
    }
  }

  async function runConfirm(): Promise<void> {
    if (!confirmCode.trim()) {
      toast.error("Zadaj 6 miestny kód.");
      return;
    }
    try {
      await hivePostJson<{ verified: boolean }>("auth/profile/totp/confirm", { code: confirmCode });
      toast.success("2FA aktivovaná");
      setConfirmCode("");
      setProvisionOut(null);
      await reload();
    } catch (e) {
      if (e instanceof HiveApiError) toast.error(e.message);
      else toast.error("Potvrdenie OTP zlyhalo.");
    }
  }

  async function runDisable(): Promise<void> {
    if (!disablePwd.trim()) {
      toast.error("Zadaj heslo na vypnutie.");
      return;
    }
    try {
      const next = await hivePostJson<DashboardOperatorMe>("auth/profile/totp/disable", { password: disablePwd });
      setMe(next);
      setProvisionOut(null);
      setDisablePwd("");
      toast.success("2FA vypnutá");
    } catch (e) {
      if (e instanceof HiveApiError) toast.error(e.message);
      else toast.error("Vypnutie zlyhalo.");
    }
  }

  if (!me) {
    return (
      <article className="rounded-2xl border border-alert/25 bg-hive-card/90 p-6 md:p-8">
        <p className="text-sm text-danger">Security panel requires an authenticated dashboard session.</p>
      </article>
    );
  }

  return (
    <article className="space-y-8">
      <section className="rounded-2xl border border-cyan/[0.12] bg-hive-card/90 p-6 md:p-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">
              Two-factor authentication
            </h2>
            <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-muted-foreground">
              TOTP (Google Authenticator / 1Password). Stav:{" "}
              <span className="text-[#00FF88]">
                {me.totp_required ? "zapnuté" : "vypnuté"} · verified {me.totp_verified_at ? "áno" : "nie"}
              </span>
            </p>
          </div>
          <HiveSwitch
            checked={me.totp_required}
            aria-label="Two-factor enrollment status"
            onCheckedChange={(nextVal) => {
              if (!nextVal) {
                toast.error("Na vypnutie použij heslo v sekcii nižšie.");
                return;
              }
              toast.message("Prihlásenie 2FA", {
                description: "Použi provisioning (heslo → nový QR → OTP).",
              });
            }}
          />
        </div>

        <div className="mt-8 space-y-4 rounded-2xl border border-pollen/[0.15] bg-black/35 p-5">
          <p className="font-[family-name:var(--font-inter)] text-sm text-zinc-400">
            Workflow: zadaj heslo → Vygenerovať nový seed → nahraj do autentifikátora → potvrď OTP. Vypnutie vyžaduje heslo nižšie.
          </p>
          <label className="block space-y-2">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.22em] text-zinc-500">
              Heslo konta (provisioning)
            </span>
            <input
              type="password"
              autoComplete="current-password"
              value={provisionPwd}
              onChange={(e) => setProvisionPwd(e.target.value)}
              className="w-full rounded-xl border border-cyan/[0.15] bg-black/45 px-4 py-2 font-mono text-sm text-[#fafafa]"
            />
          </label>
          <NeonButton type="button" variant="ghost" className="text-xs" onClick={() => void runProvision()}>
            Vygenerovať nový QR / seed
          </NeonButton>
          {provisionOut ? (
            <div className="space-y-2 rounded-xl border border-cyan/[0.1] bg-black/40 p-4">
              <p className="font-mono text-xs text-data break-all">{provisionOut.secret_base32}</p>
              <p className="font-[family-name:var(--font-inter)] text-xs text-zinc-500 break-all">{provisionOut.otpauth_uri}</p>
              <label className="block space-y-2 pt-3">
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.22em] text-zinc-500">
                  Potvrdiť OTP
                </span>
                <input
                  value={confirmCode}
                  onChange={(e) => setConfirmCode(e.target.value)}
                  className="w-full rounded-xl border border-cyan/[0.15] bg-black/45 px-4 py-2 font-mono text-sm tracking-[0.35em]"
                />
              </label>
              <NeonButton type="button" variant="primary" className="text-xs" onClick={() => void runConfirm()}>
                Potvrdiť kód
              </NeonButton>
            </div>
          ) : null}
          <div className="flex flex-wrap gap-4 border-t border-cyan/[0.08] pt-4">
            <label className="min-w-[200px] flex-1 space-y-2">
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.22em] text-alert">
                Heslo · vypnúť 2FA úplne
              </span>
              <input
                type="password"
                autoComplete="current-password"
                value={disablePwd}
                onChange={(e) => setDisablePwd(e.target.value)}
                className="w-full rounded-xl border border-alert/25 bg-black/45 px-4 py-2 font-mono text-sm text-[#fafafa]"
              />
            </label>
            <NeonButton
              type="button"
              variant="ghost"
              className="mt-6 shrink-0 self-end text-danger"
              onClick={() => void runDisable()}
            >
              Vypnúť 2FA
            </NeonButton>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-cyan/[0.12] bg-hive-card/90 p-6 md:p-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-[family-name:var(--font-space-grotesk)] font-semibold text-[#fafafa]">Audit digest routing</p>
            <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-muted-foreground">
              Ukladá preference do Postgres JSON · integrácie Slack/email pripravené backendom.
            </p>
          </div>
          <HiveSwitch checked={auditDigest} onCheckedChange={(v) => void toggleAudit(v)} aria-label="Toggle audit routing" />
        </div>
      </section>
    </article>
  );
}
