"use client";

import { Download, ExternalLink, RefreshCw, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { SessionPolicySettingsCard } from "@/components/hive/session-policy-settings-card";
import { Toggle } from "@/components/ui/toggle";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type {
  BackupCodesRegenerateResponse,
  DashboardOperatorMe,
  TotpConfirmResponse,
  TotpProvisionResponse,
} from "@/lib/hive-dashboard-session";
import type { SessionPolicySnapshot } from "@/lib/session-policy-types";

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
  const [sessionPolicy, setSessionPolicy] = useState<SessionPolicySnapshot | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const [enrollOpen, setEnrollOpen] = useState(false);
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
      const [row, policy] = await Promise.all([
        hiveGet<DashboardOperatorMe>("auth/me"),
        hiveGet<SessionPolicySnapshot>("auth/session-policy").catch(() => null),
      ]);
      setMe(row);
      setSessionPolicy(policy);
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
      setFreshCodes(null);
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

  async function submitPasswordChange(): Promise<void> {
    if (currentPassword.length < 8 || newPassword.length < 8) {
      toast.error("Both passwords must be at least 8 characters.");
      return;
    }
    if (currentPassword === newPassword) {
      toast.error("New password must differ from current password.");
      return;
    }
    setPasswordBusy(true);
    try {
      await hivePostJson<{ ok: boolean }>("auth/me/password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      toast.success("Password changed.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Password update failed";
      toast.error(msg);
    } finally {
      setPasswordBusy(false);
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
          width: 160,
          margin: 1,
          color: { dark: "#1A0E2EFF", light: "#FFFFFFFF" },
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
  const visibleBackupCodes = freshCodes ?? [];

  return (
    <div className="flex flex-col gap-6">
      {profileUnavailable ? (
        <div
          className="rounded-2xl border border-danger/30 bg-danger/6 p-4 text-sm text-danger"
          role="alert"
        >
          <p className="font-medium">
            Could not load account status
            {err?.includes("502") || err?.includes("503")
              ? " — hive is restarting, try again in a few seconds."
              : err
                ? ` (${err}).`
                : "."}
          </p>
          <button type="button" className="qs-btn qs-btn--secondary qs-btn--sm mt-3" disabled={profileLoading} onClick={() => void loadMe()}>
            Try again
          </button>
        </div>
      ) : null}

      {twofaPending ? (
        <div className="rounded-xl border border-pollen/30 bg-pollen/6 px-4 py-3 text-sm text-(--qs-text-2)">
          Finish 2FA setup — scan the QR in Authenticator, then enter the six-digit code.
          <button type="button" className="ml-3 font-semibold text-pollen underline decoration-dotted" onClick={openEnrollFromUi}>
            Continue
          </button>
        </div>
      ) : null}

      <V4Card>
        <V4CardHeader
          title="Two-factor authentication"
          description="TOTP-based — Authenticator app, backup codes, advanced policies per RBAC role."
          actions={
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
          }
        />

        {!twofaComplete && !profileLoading ? (
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" disabled={busy} onClick={() => openEnrollFromUi()}>
              Set up 2FA
            </button>
            <a
              href="https://support.google.com/accounts/answer/1066447"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs font-semibold text-pollen underline decoration-dotted"
            >
              <ExternalLink className="h-3 w-3" aria-hidden />
              Authenticator guide
            </a>
          </div>
        ) : null}

        {twofaComplete ? (
          <div className="v4-settings-twofa-grid mt-6 grid gap-6">
            <div>
              <p className="v4-field-label mb-3">Authenticator app</p>
              <div className="grid place-items-center rounded-xl bg-[rgba(7,3,15,0.5)] p-4">
                <div className="flex h-40 w-40 flex-col items-center justify-center gap-2 rounded-lg border border-(--qs-border) bg-(--qs-surface-2)/60 p-4 text-center">
                  <ShieldCheck className="h-10 w-10 text-success" aria-hidden />
                  <p className="text-xs font-semibold text-(--qs-text-2)">Linked & verified</p>
                </div>
              </div>
              <p className="mt-3 text-center font-mono text-xs text-(--qs-text-3)">
                Secret not shown after enrollment — use backup codes if you lose the device.
              </p>
            </div>

            <div>
              <p className="v4-field-label mb-1">Backup codes</p>
              <p className="text-sm text-(--qs-text-3)">Store these somewhere safe — each works once.</p>
              <p className="mt-1 text-xs text-(--qs-text-3)">
                {backupRemaining} codes left · last used {formatBackupLastUsed(me?.totp_backup_last_used_at)}
              </p>

              <div className="mt-3 grid grid-cols-2 gap-2">
                {visibleBackupCodes.length > 0
                  ? visibleBackupCodes.map((c) => (
                      <div key={c} className="v4-backup-code">
                        {c}
                      </div>
                    ))
                  : Array.from({ length: 8 }).map((_, i) => (
                      <div key={i} className="v4-backup-code opacity-40">
                        ••••-••••
                      </div>
                    ))}
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    setRegenPassword("");
                    setRegenOpen(true);
                  }}
                  className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1.5 disabled:opacity-40"
                >
                  <RefreshCw className="h-3.5 w-3.5" aria-hidden />
                  Regenerate
                </button>
                <button
                  type="button"
                  disabled={busy || visibleBackupCodes.length === 0}
                  onClick={() => downloadBackupCodes(visibleBackupCodes)}
                  className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1.5 disabled:opacity-40"
                >
                  <Download className="h-3.5 w-3.5" aria-hidden />
                  Download .txt
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </V4Card>

      <SessionPolicySettingsCard policy={sessionPolicy} onSaved={setSessionPolicy} />

      <V4Card>
        <V4CardHeader as="h3" title="Hive password" description="Change your login password directly here." />
        <div className="grid gap-3 md:max-w-xl">
          <label className="grid gap-1.5">
            <span className="v4-field-label">Current password</span>
            <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} autoComplete="current-password" className="qs-input" />
          </label>
          <label className="grid gap-1.5">
            <span className="v4-field-label">New password</span>
            <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} autoComplete="new-password" className="qs-input" />
          </label>
          <div className="pt-1">
            <button type="button" className="qs-btn qs-btn--primary qs-btn--sm disabled:opacity-40" disabled={passwordBusy} onClick={() => void submitPasswordChange()}>
              {passwordBusy ? "Saving..." : "Change password"}
            </button>
          </div>
        </div>
      </V4Card>

      {enrollOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal>
          <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-xl border border-(--qs-border) bg-(--qs-surface-2) p-6 shadow-[var(--qs-glow-gold)]">
            <h3 className="text-lg font-semibold text-[#fafafa]">
              {enrollPhase === "password" ? "Confirm password" : "Scan QR and verify Authenticator"}
            </h3>
            {enrollPhase === "password" ? (
              <>
                <p className="mt-2 text-sm text-(--qs-text-3)">Enter your login password to generate the TOTP secret and show the QR code.</p>
                <input type="password" value={enrollPassword} onChange={(e) => setEnrollPassword(e.target.value)} className="qs-input mt-4" autoComplete="current-password" />
                <div className="mt-4 flex justify-end gap-2">
                  <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => setEnrollOpen(false)}>
                    Cancel
                  </button>
                  <button type="button" disabled={busy} className="qs-btn qs-btn--primary qs-btn--sm disabled:opacity-40" onClick={() => void submitEnrollPassword()}>
                    Next
                  </button>
                </div>
              </>
            ) : null}
            {enrollPhase === "scan" && provision ? (
              <>
                <p className="mt-3 text-sm text-(--qs-text-2)">
                  Open your authenticator app, scan the QR, then enter the six-digit code below.
                </p>
                <div className="mt-5 grid place-items-center rounded-xl bg-white p-3">
                  {qrBusy ? (
                    <div className="flex h-40 w-40 items-center justify-center text-xs text-(--qs-text-3)">Building QR…</div>
                  ) : qrDisplaySrc ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={qrDisplaySrc} alt="TOTP QR code" width={160} height={160} className="block h-40 w-40" />
                  ) : (
                    <div className="flex h-40 w-40 items-center px-3 text-center text-[11px] text-(--qs-text-3)">QR unavailable — use manual key below.</div>
                  )}
                </div>
                <p className="mt-3 text-center font-mono text-xs text-pollen">{provision.secret_base32}</p>
                <label className="mt-6 block">
                  <span className="v4-field-label">Code from Authenticator (6 digits)</span>
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
                    className="qs-input mt-2 w-full max-w-[200px] py-3 text-center font-mono text-xl tracking-[0.35em]"
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
                  <button type="button" disabled={busy || confirmCode.length < 6} className="qs-btn qs-btn--primary qs-btn--sm disabled:opacity-40" onClick={() => void submitConfirmTotp()}>
                    Verify & enable 2FA
                  </button>
                </div>
              </>
            ) : null}
          </div>
        </div>
      ) : null}

      {disableOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-sm rounded-xl border border-(--qs-border) bg-(--qs-surface-2) p-6">
            <h3 className="text-lg font-semibold text-[#fafafa]">Disable 2FA</h3>
            <p className="mt-2 text-sm text-(--qs-text-3)">Enter your password to remove TOTP.</p>
            <input type="password" value={disablePassword} onChange={(e) => setDisablePassword(e.target.value)} className="qs-input mt-4" />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => setDisableOpen(false)}>
                Cancel
              </button>
              <button type="button" disabled={busy} className="qs-btn qs-btn--danger qs-btn--sm disabled:opacity-40" onClick={() => void submitDisable()}>
                Disable
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {regenOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-sm rounded-xl border border-(--qs-border) bg-(--qs-surface-2) p-6">
            <h3 className="text-lg font-semibold">Regenerate codes</h3>
            <p className="mt-2 text-sm text-(--qs-text-3)">Old backup codes will stop working.</p>
            <input type="password" value={regenPassword} onChange={(e) => setRegenPassword(e.target.value)} className="qs-input mt-4" />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => setRegenOpen(false)}>
                Cancel
              </button>
              <button type="button" disabled={busy} className="qs-btn qs-btn--primary qs-btn--sm disabled:opacity-40" onClick={() => void submitRegenerate()}>
                Generate
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {freshCodes?.length ? (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/75 p-4">
          <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-xl border border-pollen/35 bg-(--qs-surface-2) p-6">
            <h3 className="text-lg font-semibold text-pollen">Save your codes</h3>
            <p className="mt-2 text-sm text-(--qs-text-2)">Shown only now. Each code is single-use at sign-in.</p>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {freshCodes.map((c) => (
                <div key={c} className="v4-backup-code">
                  {c}
                </div>
              ))}
            </div>
            <div className="mt-6 flex flex-wrap gap-2">
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1.5" onClick={() => downloadBackupCodes(freshCodes)}>
                <Download className="h-3.5 w-3.5" aria-hidden />
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
