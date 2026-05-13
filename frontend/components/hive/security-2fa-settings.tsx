"use client";

import { ExternalLink, Grid2x2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { HiveSwitch } from "@/components/ui/hive-switch";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type {
  BackupCodesRegenerateResponse,
  DashboardOperatorMe,
  TotpConfirmResponse,
  TotpProvisionResponse,
} from "@/lib/hive-dashboard-session";

function formatBackupLastUsed(iso: string | null | undefined): string {
  if (!iso) {
    return "nikdy";
  }
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return "—";
  }
  const days = Math.floor((Date.now() - d.getTime()) / 86_400_000);
  if (days < 1) {
    return "dnes";
  }
  if (days === 1) {
    return "pred 1 dňom";
  }
  return `pred ${days} dňami`;
}

function downloadBackupCodes(codes: string[]): void {
  const blob = new Blob([`${codes.join("\n")}\n`], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "queenswarm-backup-codes.txt";
  a.click();
  URL.revokeObjectURL(url);
}

export function Security2FASettings() {
  const [me, setMe] = useState<DashboardOperatorMe | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [enrollOpen, setEnrollOpen] = useState(false);
  const [enrollPhase, setEnrollPhase] = useState<"password" | "qr" | "confirm">("password");
  const [enrollPassword, setEnrollPassword] = useState("");
  const [provision, setProvision] = useState<TotpProvisionResponse | null>(null);
  const [confirmCode, setConfirmCode] = useState("");

  const [disableOpen, setDisableOpen] = useState(false);
  const [disablePassword, setDisablePassword] = useState("");

  const [regenOpen, setRegenOpen] = useState(false);
  const [regenPassword, setRegenPassword] = useState("");
  const [freshCodes, setFreshCodes] = useState<string[] | null>(null);

  const loadMe = useCallback(async () => {
    try {
      const row = await hiveGet<DashboardOperatorMe>("auth/me");
      setMe(row);
      setErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Profil nedostupný";
      setErr(msg);
      setMe(null);
    }
  }, []);

  useEffect(() => {
    void loadMe();
  }, [loadMe]);

  const twofaComplete = Boolean(me?.totp_verified_at && me?.totp_has_secret);
  const twofaPending = Boolean(me?.totp_has_secret && !me?.totp_verified_at);

  const backupRemaining = me?.totp_backup_codes_remaining ?? 0;

  function openEnrollFromUi(): void {
    setEnrollPassword("");
    setConfirmCode("");
    setProvision(null);
    if (twofaPending) {
      setEnrollPhase("confirm");
    } else {
      setEnrollPhase("password");
    }
    setEnrollOpen(true);
  }

  async function submitEnrollPassword(): Promise<void> {
    if (enrollPassword.length < 8) {
      toast.error("Zadaj platné heslo.");
      return;
    }
    setBusy(true);
    try {
      const prov = await hivePostJson<TotpProvisionResponse>("auth/profile/totp/provision", {
        password: enrollPassword,
      });
      setProvision(prov);
      setEnrollPhase("qr");
      toast.success("Naskenuj QR kód alebo zadaj kľúč ručne.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Provision zlyhal";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function submitConfirmTotp(): Promise<void> {
    const c = confirmCode.trim();
    if (c.length < 6) {
      toast.error("Zadaj 6-miestny TOTP kód.");
      return;
    }
    setBusy(true);
    try {
      const res = await hivePostJson<TotpConfirmResponse>("auth/profile/totp/confirm", { code: c });
      await loadMe();
      setEnrollOpen(false);
      if (res.backup_codes?.length) {
        setFreshCodes(res.backup_codes);
        toast.success("2FA je aktívne. Ulož si záložné kódy.");
      } else {
        toast.success("2FA je aktívne.");
      }
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Neplatný kód";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function submitDisable(): Promise<void> {
    if (disablePassword.length < 8) {
      toast.error("Zadaj heslo.");
      return;
    }
    setBusy(true);
    try {
      const row = await hivePostJson<DashboardOperatorMe>("auth/profile/totp/disable", {
        password: disablePassword,
      });
      setMe(row);
      setDisableOpen(false);
      setDisablePassword("");
      toast.success("2FA bolo vypnuté.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Zlyhalo";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function submitRegenerate(): Promise<void> {
    if (regenPassword.length < 8) {
      toast.error("Zadaj heslo.");
      return;
    }
    setBusy(true);
    try {
      const res = await hivePostJson<BackupCodesRegenerateResponse>("auth/profile/totp/backup-codes/regenerate", {
        password: regenPassword,
      });
      setRegenOpen(false);
      setRegenPassword("");
      setFreshCodes(res.codes);
      await loadMe();
      toast.success("Nové záložné kódy vygenerované.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Regenerácia zlyhala";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  const qrSrc = useMemo(() => {
    if (!provision?.otpauth_uri) {
      return null;
    }
    return `https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(provision.otpauth_uri)}`;
  }, [provision?.otpauth_uri]);

  if (err && !me) {
    return (
      <div className="rounded-3xl border border-danger/30 bg-danger/[0.06] p-6 text-sm text-danger">
        Nepodarilo sa načítať nastavenia: {err}
      </div>
    );
  }

  if (!me) {
    return <div className="h-48 animate-pulse rounded-3xl bg-white/[0.04]" />;
  }

  return (
    <div className="flex flex-col gap-6">
      {twofaPending ? (
        <div className="rounded-2xl border border-pollen/35 bg-pollen/[0.06] px-4 py-3 font-[family-name:var(--font-inter)] text-sm text-zinc-200">
          Dokonči nastavenie 2FA — zadaj kód z aplikácie (Google Authenticator alebo kompatibilná).
          <button
            type="button"
            className="ml-3 font-semibold text-pollen underline decoration-dotted"
            onClick={openEnrollFromUi}
          >
            Pokračovať
          </button>
        </div>
      ) : null}

      <section className="rounded-3xl border border-white/[0.08] bg-[#0c0c14]/95 p-6 md:p-7">
        <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">
          Aplikácia Google Authenticator
        </h2>
        <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
          Queenswarm používa štandardný TOTP kľúč (rovnako ako účty Google pri 2‑krokovej verifikácii). Najprv si nainštaluj aplikáciu a potom aktivuj prepínač nižšie.
        </p>
        <ul className="mt-4 flex flex-col gap-2 font-[family-name:var(--font-inter)] text-sm">
          <li>
            <a
              href="https://support.google.com/accounts/answer/1066447"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 font-semibold text-pollen underline decoration-dotted underline-offset-2 hover:text-[#ffc933]"
            >
              <ExternalLink className="h-3.5 w-3.5" aria-hidden /> Google návod k 2FA / Authenticator
            </a>
          </li>
          <li>
            <a
              href="https://apps.apple.com/sk/app/google-authenticator/id388497605"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 font-semibold text-pollen underline decoration-dotted underline-offset-2 hover:text-[#ffc933]"
            >
              <ExternalLink className="h-3.5 w-3.5" aria-hidden /> App Store — Google Authenticator
            </a>
          </li>
          <li>
            <a
              href="https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 font-semibold text-pollen underline decoration-dotted underline-offset-2 hover:text-[#ffc933]"
            >
              <ExternalLink className="h-3.5 w-3.5" aria-hidden /> Google Play — Authenticator
            </a>
          </li>
        </ul>
      </section>

      <section className="rounded-3xl border border-white/[0.08] bg-[#0c0c14]/95 p-6 md:p-7">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">
              Two-factor authentication
            </h2>
            <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
              TOTP (časové kódy cez aplikáciu typu Authenticator alebo ekvivalent).
            </p>
          </div>
          <HiveSwitch
            checked={twofaComplete}
            onCheckedChange={(next) => {
              if (next) {
                if (!twofaComplete) {
                  openEnrollFromUi();
                }
              } else {
                setDisablePassword("");
                setDisableOpen(true);
              }
            }}
            disabled={busy}
            aria-label="Zapnúť alebo vypnúť 2FA"
          />
        </div>

        {twofaComplete ? (
          <div className="mt-6 rounded-2xl border border-white/[0.07] bg-black/40 p-5">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-white/15 bg-black/40">
                <Grid2x2 className="h-6 w-6 text-zinc-300" aria-hidden />
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="font-[family-name:var(--font-space-grotesk)] text-base font-semibold text-[#fafafa]">
                  Backup codes
                </h3>
                <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
                  {backupRemaining} kódov zostáva · naposledy použité{" "}
                  {formatBackupLastUsed(me.totp_backup_last_used_at)}
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => {
                      setRegenPassword("");
                      setRegenOpen(true);
                    }}
                    className="rounded-full border border-white/20 bg-black/50 px-4 py-2 font-[family-name:var(--font-inter)] text-xs font-semibold text-zinc-200 transition hover:border-pollen/40 hover:text-pollen disabled:opacity-40"
                  >
                    Regenerate
                  </button>
                  <button
                    type="button"
                    disabled={busy || backupRemaining < 1}
                    onClick={() => toast.message("Stiahni nové kódy po „Regenerate“ — plaintext sa ukáže raz.")}
                    className="rounded-full border border-white/20 bg-black/50 px-4 py-2 font-[family-name:var(--font-inter)] text-xs font-semibold text-zinc-200 transition hover:border-pollen/40 hover:text-pollen disabled:opacity-40"
                  >
                    Download
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </section>

      {enrollOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal>
          <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-3xl border border-white/10 bg-[#0a0a12] p-6 shadow-[0_0_48px_rgb(255_184_0/0.12)]">
            <h3 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">
              {enrollPhase === "password" ? "Potvrď heslo" : enrollPhase === "qr" ? "Naskenuj QR" : "Potvrď TOTP"}
            </h3>
            {enrollPhase === "password" ? (
              <>
                <p className="mt-2 text-sm text-zinc-500">Na vygenerovanie nového TOTP kľúča zadaj svoje heslo.</p>
                <input
                  type="password"
                  value={enrollPassword}
                  onChange={(e) => setEnrollPassword(e.target.value)}
                  className="mt-4 w-full rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 text-sm text-[#fafafa] outline-none focus:border-pollen/40"
                  autoComplete="current-password"
                />
                <div className="mt-4 flex justify-end gap-2">
                  <button
                    type="button"
                    className="rounded-xl px-4 py-2 text-sm text-zinc-400 hover:text-[#fafafa]"
                    onClick={() => setEnrollOpen(false)}
                  >
                    Zrušiť
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-xl border border-pollen bg-pollen px-4 py-2 text-sm font-bold text-black disabled:opacity-40"
                    onClick={() => void submitEnrollPassword()}
                  >
                    Ďalej
                  </button>
                </div>
              </>
            ) : null}
            {enrollPhase === "qr" && provision ? (
              <>
                <div className="mt-4 flex justify-center">
                  {qrSrc ? (
                    // eslint-disable-next-line @next/next/no-img-element -- third-party QR API has dynamic data URL
                    <img src={qrSrc} alt="QR pre TOTP" className="h-40 w-40 rounded-xl border border-white/10" width={160} height={160} />
                  ) : null}
                </div>
                <p className="mt-3 font-[family-name:var(--font-jetbrains-mono)] text-[11px] break-all text-zinc-400">
                  {provision.secret_base32}
                </p>
                <button
                  type="button"
                  className="mt-4 w-full rounded-xl border border-cyan/30 py-2 text-sm text-cyan"
                  onClick={() => setEnrollPhase("confirm")}
                >
                  Mám naskenované — zadať kód
                </button>
              </>
            ) : null}
            {enrollPhase === "confirm" ? (
              <>
                {!provision && twofaPending ? (
                  <p className="mt-2 text-sm text-zinc-500">Zadaj 6-miestny kód z aplikácie na dokončenie.</p>
                ) : null}
                <input
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={confirmCode}
                  onChange={(e) => setConfirmCode(e.target.value)}
                  placeholder="123456"
                  className="mt-4 w-full rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 text-sm text-[#fafafa] outline-none focus:border-pollen/40"
                />
                <div className="mt-4 flex justify-end gap-2">
                  <button type="button" className="rounded-xl px-4 py-2 text-sm text-zinc-400" onClick={() => setEnrollOpen(false)}>
                    Zrušiť
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-xl border border-pollen bg-pollen px-4 py-2 text-sm font-bold text-black disabled:opacity-40"
                    onClick={() => void submitConfirmTotp()}
                  >
                    Overiť
                  </button>
                </div>
              </>
            ) : null}
          </div>
        </div>
      ) : null}

      {disableOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-sm rounded-3xl border border-white/10 bg-[#0a0a12] p-6">
            <h3 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">Vypnúť 2FA</h3>
            <p className="mt-2 text-sm text-zinc-500">Zadaj heslo na odstránenie TOTP.</p>
            <input
              type="password"
              value={disablePassword}
              onChange={(e) => setDisablePassword(e.target.value)}
              className="mt-4 w-full rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 text-sm outline-none"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" className="rounded-xl px-3 py-2 text-sm text-zinc-400" onClick={() => setDisableOpen(false)}>
                Zrušiť
              </button>
              <button
                type="button"
                disabled={busy}
                className="rounded-xl bg-danger/80 px-3 py-2 text-sm font-semibold text-white disabled:opacity-40"
                onClick={() => void submitDisable()}
              >
                Vypnúť
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {regenOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-sm rounded-3xl border border-white/10 bg-[#0a0a12] p-6">
            <h3 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold">Regenerovať kódy</h3>
            <p className="mt-2 text-sm text-zinc-500">Staré záložné kódy prestanú platiť.</p>
            <input
              type="password"
              value={regenPassword}
              onChange={(e) => setRegenPassword(e.target.value)}
              className="mt-4 w-full rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 text-sm outline-none"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" className="rounded-xl px-3 py-2 text-sm text-zinc-400" onClick={() => setRegenOpen(false)}>
                Zrušiť
              </button>
              <button
                type="button"
                disabled={busy}
                className="rounded-xl border border-pollen bg-pollen/90 px-3 py-2 text-sm font-bold text-black disabled:opacity-40"
                onClick={() => void submitRegenerate()}
              >
                Vygenerovať
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {freshCodes?.length ? (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/75 p-4">
          <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-3xl border border-pollen/30 bg-[#0a0a12] p-6">
            <h3 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-pollen">Ulož si kódy</h3>
            <p className="mt-2 text-sm text-zinc-400">Zobrazia sa len teraz. Každý kód je jednorazový pri prihlásení.</p>
            <ul className="mt-4 space-y-1 font-[family-name:var(--font-jetbrains-mono)] text-sm text-[#fafafa]">
              {freshCodes.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
            <div className="mt-6 flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-xl border border-white/20 px-4 py-2 text-sm text-zinc-200"
                onClick={() => downloadBackupCodes(freshCodes)}
              >
                Stiahnuť .txt
              </button>
              <button
                type="button"
                className="rounded-xl bg-pollen px-4 py-2 text-sm font-bold text-black"
                onClick={() => setFreshCodes(null)}
              >
                Rozumiem
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
