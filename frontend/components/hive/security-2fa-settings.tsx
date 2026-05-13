"use client";

import { ExternalLink, Grid2x2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Toggle } from "@/components/ui/toggle";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type {
  BackupCodesRegenerateResponse,
  DashboardOperatorMe,
  TotpConfirmResponse,
  TotpProvisionResponse,
} from "@/lib/hive-dashboard-session";

function formatBackupLastUsed(iso: string | null | undefined): string {
  if (!iso) {
    return "never";
  }
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return "—";
  }
  const days = Math.floor((Date.now() - d.getTime()) / 86_400_000);
  if (days < 1) {
    return "today";
  }
  if (days === 1) {
    return "1 day ago";
  }
  return `${days} days ago`;
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
  const [profileLoading, setProfileLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const [enrollOpen, setEnrollOpen] = useState(false);
  /** password → hive password + provision · scan → QR + manual secret + 6-digit verify (never code-only). */
  const [enrollPhase, setEnrollPhase] = useState<"password" | "scan">("password");
  const [enrollPassword, setEnrollPassword] = useState("");
  const [provision, setProvision] = useState<TotpProvisionResponse | null>(null);
  const [confirmCode, setConfirmCode] = useState("");

  const [disableOpen, setDisableOpen] = useState(false);
  const [disablePassword, setDisablePassword] = useState("");

  const [regenOpen, setRegenOpen] = useState(false);
  const [regenPassword, setRegenPassword] = useState("");
  const [freshCodes, setFreshCodes] = useState<string[] | null>(null);

  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [qrBusy, setQrBusy] = useState(false);

  const loadMe = useCallback(async () => {
    setProfileLoading(true);
    try {
      const row = await hiveGet<DashboardOperatorMe>("auth/me");
      setMe(row);
      setErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Profile unavailable";
      setErr(msg);
      setMe(null);
    } finally {
      setProfileLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadMe();
  }, [loadMe]);

  const twofaComplete = Boolean(me?.totp_verified_at && me?.totp_has_secret);
  const twofaPending = Boolean(me?.totp_has_secret && !me?.totp_verified_at);

  const backupRemaining = me?.totp_backup_codes_remaining ?? 0;
  const profileUnavailable = Boolean(err) && me === null && !profileLoading;

  function openEnrollFromUi(): void {
    setEnrollPassword("");
    setConfirmCode("");
    setProvision(null);
    setQrDataUrl(null);
    setEnrollPhase("password");
    setEnrollOpen(true);
  }

  async function submitEnrollPassword(): Promise<void> {
    if (enrollPassword.length < 8) {
      toast.error("Enter a valid password.");
      return;
    }
    setBusy(true);
    try {
      const prov = await hivePostJson<TotpProvisionResponse>("auth/profile/totp/provision", {
        password: enrollPassword,
      });
      setProvision(prov);
      setEnrollPhase("scan");
      toast.success("Scan the QR code or enter the key manually.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Provisioning failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function submitConfirmTotp(rawCode?: string): Promise<void> {
    const c = (rawCode ?? confirmCode).trim();
    if (c.length < 6) {
      toast.error("Enter a 6-digit TOTP code.");
      return;
    }
    setBusy(true);
    try {
      const res = await hivePostJson<TotpConfirmResponse>("auth/profile/totp/confirm", { code: c });
      await loadMe();
      setEnrollOpen(false);
      setEnrollPhase("password");
      setProvision(null);
      setConfirmCode("");
      setQrDataUrl(null);
      if (res.backup_codes?.length) {
        setFreshCodes(res.backup_codes);
        toast.success("2FA is on. Save your backup codes.");
      } else {
        toast.success("2FA is on.");
      }
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Invalid code";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function submitDisable(): Promise<void> {
    if (disablePassword.length < 8) {
      toast.error("Enter your password.");
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
      toast.success("2FA has been disabled.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Request failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function submitRegenerate(): Promise<void> {
    if (regenPassword.length < 8) {
      toast.error("Enter your password.");
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
      toast.success("New backup codes generated.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Regeneration failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    const uri = provision?.otpauth_uri?.trim();
    if (!uri || enrollPhase !== "scan") {
      return;
    }
    let cancelled = false;
    setQrBusy(true);
    void (async () => {
      try {
        const QR = await import("qrcode");
        const dataUrl = await QR.toDataURL(uri, {
          width: 200,
          margin: 1,
          color: { dark: "#050510FF", light: "#FFFFFFFF" },
        });
        if (!cancelled) setQrDataUrl(dataUrl);
      } catch {
        if (!cancelled) setQrDataUrl(null);
      } finally {
        if (!cancelled) setQrBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [provision?.otpauth_uri, enrollPhase]);

  const qrFallbackRemote = provision?.otpauth_uri
    ? `https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(provision.otpauth_uri)}`
    : null;
  const qrDisplaySrc = qrDataUrl ?? qrFallbackRemote;

  return (
    <div className="flex flex-col gap-6">
      {profileUnavailable ? (
        <div
          className="rounded-2xl border-[length:var(--qs-bubble-border-width)] border-solid border-danger/30 bg-danger/[0.06] p-4 font-[family-name:var(--font-poppins)] text-sm text-danger"
          role="alert"
        >
          <p className="font-medium">Could not load account status ({err}).</p>
          <p className="mt-1 text-xs text-danger/80">
            The 2FA guide and controls below still work; reload the profile to see the latest state.
          </p>
          <button
            type="button"
            className="qs-btn qs-btn--secondary qs-btn--sm mt-3"
            disabled={profileLoading}
            onClick={() => void loadMe()}
          >
            Try again
          </button>
        </div>
      ) : null}
      <section className="rounded-3xl qs-rim-cyan-soft bg-[#0c0c14]/95 p-6 md:p-7">
        <h2 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#fafafa]">Hive password</h2>
        <p className="mt-2 font-[family-name:var(--font-poppins)] text-sm text-zinc-400">
          Operator passwords are provisioned through the bootstrap / admin flows on the API today. Use the same password you authenticate with at login; self-service rotation ships in a
          follow-on release.
        </p>
        <p className="mt-3 font-[family-name:var(--font-poppins)] text-xs text-zinc-500">
          Need a reset? Re-seed the queen account via infrastructure playbooks or contact the hive admin.
        </p>
      </section>
      {twofaPending ? (
        <div className="rounded-2xl border-[length:var(--qs-bubble-border-width)] border-solid border-pollen/35 bg-pollen/[0.06] px-4 py-3 font-[family-name:var(--font-poppins)] text-sm text-zinc-200">
          Finish 2FA setup — open the wizard, enter your password again, scan the QR in Authenticator first,
          then enter the six-digit code in the same dialog.
          <button type="button" className="ml-3 font-semibold text-pollen underline decoration-dotted" onClick={openEnrollFromUi}>
            Continue
          </button>
        </div>
      ) : null}

      <section className="rounded-3xl qs-rim bg-[#0c0c14]/95 p-6 md:p-7">
        <h2 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#fafafa]">
          Google Authenticator app
        </h2>
        <p className="mt-1 font-[family-name:var(--font-poppins)] text-sm text-zinc-500">
          Queenswarm uses a standard TOTP secret (same idea as Google 2-step verification). Install an authenticator app, then use the toggle below.
        </p>
        <ul className="mt-4 flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-sm">
          <li>
            <a
              href="https://support.google.com/accounts/answer/1066447"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 font-semibold text-pollen underline decoration-dotted underline-offset-2 hover:text-[#ffc933]"
            >
              <ExternalLink className="h-3.5 w-3.5" aria-hidden /> Google guide — 2FA / Authenticator
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

      <section className="rounded-3xl qs-rim bg-[#0c0c14]/95 p-6 md:p-7">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#fafafa]">
              Two-factor authentication
            </h2>
            <p className="mt-1 font-[family-name:var(--font-poppins)] text-sm text-zinc-500">
              TOTP (time-based codes from an Authenticator-style app).
            </p>
            {profileLoading ? (
              <p className="mt-2 font-[family-name:var(--font-poppins)] text-xs text-zinc-500">Loading account status…</p>
            ) : null}
          </div>
          <Toggle
            checked={twofaComplete}
            onChange={(next) => {
              if (next) {
                if (!twofaComplete) {
                  openEnrollFromUi();
                }
              } else {
                setDisablePassword("");
                setDisableOpen(true);
              }
            }}
            disabled={busy || profileLoading}
            aria-label="Turn 2FA on or off"
          />
        </div>

        {!twofaComplete && !profileLoading ? (
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" disabled={busy} onClick={() => openEnrollFromUi()}>
              Set up 2FA
            </button>
            <span className="font-[family-name:var(--font-poppins)] text-xs text-zinc-500">
              Or use the toggle — that opens the wizard: password → QR, then the 6-digit code.
            </span>
          </div>
        ) : null}

        {twofaComplete ? (
          <div className="mt-6 rounded-2xl qs-rim bg-black/40 p-5">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl qs-rim bg-black/40">
                <Grid2x2 className="h-6 w-6 text-zinc-300" aria-hidden />
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="font-[family-name:var(--font-poppins)] text-base font-semibold text-[#fafafa]">
                  Backup codes
                </h3>
                <p className="mt-1 font-[family-name:var(--font-poppins)] text-sm text-zinc-500">
                  {backupRemaining} codes left · last used{" "}
                  {formatBackupLastUsed(me?.totp_backup_last_used_at)}
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => {
                      setRegenPassword("");
                      setRegenOpen(true);
                    }}
                    className="qs-btn qs-btn--ghost qs-btn--sm disabled:opacity-40"
                  >
                    Regenerate
                  </button>
                  <button
                    type="button"
                    disabled={busy || backupRemaining < 1}
                    onClick={() => toast.message("Download new codes after “Regenerate” — plaintext is shown once.")}
                    className="qs-btn qs-btn--ghost qs-btn--sm disabled:opacity-40"
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
          <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-3xl qs-rim bg-[#0a0a12] p-6 shadow-[0_0_48px_rgb(255_184_0/0.12)]">
            <h3 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#fafafa]">
              {enrollPhase === "password" ? "Confirm password" : "Scan QR and verify Authenticator"}
            </h3>
            {enrollPhase === "password" ? (
              <>
                <p className="mt-2 text-sm text-zinc-500">
                  Enter your login password to generate the TOTP secret and show the QR code.
                  {twofaPending ? (
                    <span className="mt-1 block text-xs text-zinc-500">
                      In-progress setup will finish with a new secret after password check.
                    </span>
                  ) : null}
                </p>
                <input
                  type="password"
                  value={enrollPassword}
                  onChange={(e) => setEnrollPassword(e.target.value)}
                  className="qs-input mt-4"
                  autoComplete="current-password"
                />
                <div className="mt-4 flex justify-end gap-2">
                  <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => setEnrollOpen(false)}>
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    className="qs-btn qs-btn--primary qs-btn--sm disabled:opacity-40"
                    onClick={() => void submitEnrollPassword()}
                  >
                    Next
                  </button>
                </div>
              </>
            ) : null}
            {enrollPhase === "scan" && provision ? (
              <>
                <p className="mt-3 text-sm leading-relaxed text-zinc-400">
                  Open <strong className="text-[#fafafa]">Google Authenticator</strong>, tap{" "}
                  <strong className="text-[#fafafa]">+</strong> → <strong className="text-[#fafafa]">Scan QR code</strong>, then
                  aim at the QR. After scanning, enter the six-digit code below — same screen, no hidden steps without QR.
                </p>

                <div className="mt-5 flex flex-wrap items-start gap-5">
                  <div className="shrink-0 rounded-xl bg-white p-3 shadow-[inset_0_0_0_1px_rgba(30,30,53,1)]">
                    {qrBusy ? (
                      <div className="flex h-[200px] w-[200px] items-center justify-center text-xs text-zinc-600">Building QR…</div>
                    ) : qrDisplaySrc ? (
                      // eslint-disable-next-line @next/next/no-img-element -- data URLs ok here.
                      <img src={qrDisplaySrc} alt="TOTP QR code" width={200} height={200} className="block h-[200px] w-[200px]" />
                    ) : (
                      <div className="flex h-[200px] w-[196px] items-center px-3 text-center text-[11px] text-zinc-600">
                        QR unavailable — enter the manual key below the QR area.
                      </div>
                    )}
                  </div>
                  <div className="min-w-[180px] max-w-full flex-1">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-zinc-500">Manual key (backup)</p>
                    <p className="mt-2 break-all font-[family-name:var(--font-poppins)] text-xs leading-relaxed text-pollen">
                      {provision.secret_base32}
                    </p>
                  </div>
                </div>

                <label className="mt-6 block">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-zinc-500">Code from Authenticator (6 digits)</span>
                  <input
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={confirmCode}
                    maxLength={6}
                    placeholder="••••••"
                    onChange={(e) => setConfirmCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                    onKeyDown={(e) => {
                      if (e.key !== "Enter" || busy) return;
                      const raw = e.currentTarget.value.replace(/\D/g, "").slice(0, 6);
                      if (raw.length >= 6) void submitConfirmTotp(raw);
                    }}
                    className="qs-input mt-2 w-full max-w-[200px] py-3 text-center !font-[family-name:var(--font-poppins)] text-xl tracking-[0.35em]"
                  />
                </label>
                <div className="mt-4 flex flex-wrap justify-end gap-2">
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    onClick={() => {
                      setEnrollOpen(false);
                      setProvision(null);
                      setConfirmCode("");
                      setEnrollPhase("password");
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={busy || confirmCode.length < 6}
                    className="qs-btn qs-btn--primary qs-btn--sm disabled:opacity-40"
                    onClick={() => void submitConfirmTotp()}
                  >
                    Verify & enable 2FA
                  </button>
                </div>
              </>
            ) : enrollPhase === "scan" && !provision ? (
              <p className="mt-4 text-sm text-zinc-500">No QR data yet — start from password (“Confirm password”).</p>
            ) : null}
          </div>
        </div>
      ) : null}

      {disableOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-sm rounded-3xl qs-rim bg-[#0a0a12] p-6">
            <h3 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#fafafa]">Disable 2FA</h3>
            <p className="mt-2 text-sm text-zinc-500">Enter your password to remove TOTP.</p>
            <input
              type="password"
              value={disablePassword}
              onChange={(e) => setDisablePassword(e.target.value)}
              className="qs-input mt-4"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => setDisableOpen(false)}>
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                className="qs-btn qs-btn--danger qs-btn--sm disabled:opacity-40"
                onClick={() => void submitDisable()}
              >
                Disable
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {regenOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-sm rounded-3xl qs-rim bg-[#0a0a12] p-6">
            <h3 className="font-[family-name:var(--font-poppins)] text-lg font-semibold">Regenerate codes</h3>
            <p className="mt-2 text-sm text-zinc-500">Old backup codes will stop working.</p>
            <input
              type="password"
              value={regenPassword}
              onChange={(e) => setRegenPassword(e.target.value)}
              className="qs-input mt-4"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => setRegenOpen(false)}>
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                className="qs-btn qs-btn--primary qs-btn--sm disabled:opacity-40"
                onClick={() => void submitRegenerate()}
              >
                Generate
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {freshCodes?.length ? (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/75 p-4">
          <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-3xl border-[length:var(--qs-bubble-border-width)] border-solid border-pollen/30 bg-[#0a0a12] p-6">
            <h3 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-pollen">Save your codes</h3>
            <p className="mt-2 text-sm text-zinc-400">Shown only now. Each code is single-use at sign-in.</p>
            <ul className="mt-4 space-y-1 font-[family-name:var(--font-poppins)] text-sm tracking-wide text-[#fafafa]">
              {freshCodes.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
            <div className="mt-6 flex flex-wrap gap-2">
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => downloadBackupCodes(freshCodes)}>
                Download .txt
              </button>
              <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" onClick={() => setFreshCodes(null)}>
                Got it
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
