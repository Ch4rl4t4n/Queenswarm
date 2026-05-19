"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { ArrowRight, Eye, EyeOff, Lock, Mail, Shield } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { LoginCardShell } from "@/components/auth/login-card-shell";
import { LoginOtpInput } from "@/components/auth/login-otp-input";

type LoginStep = "credentials" | "otp";

interface LoginUpstreamResponse {
  ok?: boolean;
  requires_totp?: boolean;
  requires_2fa?: boolean;
  mfa_required?: boolean;
  pre_auth_token?: string | null;
  mfa_token?: string | null;
  temp_token?: string | null;
  detail?: string;
  message?: string;
  access_token?: string;
  token?: string;
  expires_in?: number;
}

function persistSessionToken(token: string, expiresIn?: number): void {
  const maxAgeRaw = typeof expiresIn === "number" ? expiresIn : 1800;
  const maxAge = Math.max(120, maxAgeRaw);
  localStorage.setItem("qs_token", token.trim());
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `qs_token=${encodeURIComponent(token.trim())}; Path=/; Max-Age=${String(maxAge)}; SameSite=Lax${secure}`;
}

function LoginFormInner(): JSX.Element {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath =
    searchParams.get("next") && searchParams.get("next")!.startsWith("/") ? searchParams.get("next")! : "/";
  const forceOTPTest = searchParams.get("test_2fa") === "1";
  const startOnOtp = searchParams.get("otp") === "1";
  const isDev = process.env.NODE_ENV === "development";
  const allowDevBypass = process.env.NEXT_PUBLIC_ALLOW_DEV_LOGIN_BYPASS === "true";

  const [step, setStep] = useState<LoginStep>("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [useBackupCode, setUseBackupCode] = useState(false);
  const [backupCode, setBackupCode] = useState("");
  const [preAuthToken, setPreAuthToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hiveOnline, setHiveOnline] = useState<boolean | null>(null);
  const [hiveLatencyMs, setHiveLatencyMs] = useState<number | null>(null);
  const otpSubmitLock = useRef(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/auth/bearer", { credentials: "include" });
        if (cancelled || !res.ok) {
          return;
        }
        router.replace(nextPath);
      } catch {
        /* stay on login */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router, nextPath]);

  useEffect(() => {
    if (!startOnOtp && !forceOTPTest) {
      return;
    }
    const pre =
      window.sessionStorage.getItem("qs_pre_auth_token") ?? window.sessionStorage.getItem("qs_pre_auth");
    if (pre) {
      setPreAuthToken(pre);
      setStep("otp");
    }
  }, [startOnOtp, forceOTPTest]);

  useEffect(() => {
    let alive = true;
    void (async () => {
      const started = performance.now();
      try {
        const res = await fetch("/health", { cache: "no-store" });
        if (alive) {
          setHiveOnline(res.ok);
          setHiveLatencyMs(Math.round(performance.now() - started));
        }
      } catch {
        if (alive) {
          setHiveOnline(false);
          setHiveLatencyMs(null);
        }
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  async function handleLogin(): Promise<void> {
    if (!password) {
      setError("Enter your password");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const r = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
        credentials: "include",
      });
      const data = (await r.json()) as LoginUpstreamResponse;

      const errMsg =
        typeof data.detail === "string"
          ? data.detail
          : typeof data.message === "string"
            ? data.message
            : "Invalid credentials";

      if (!r.ok) {
        setError(errMsg);
        return;
      }

      if (forceOTPTest) {
        setStep("otp");
        return;
      }

      const preRaw =
        (typeof data.pre_auth_token === "string" ? data.pre_auth_token.trim() : "") ||
        (typeof data.mfa_token === "string" ? data.mfa_token.trim() : "") ||
        (typeof data.temp_token === "string" ? data.temp_token.trim() : "") ||
        "";

      const needsOtp = Boolean(data.requires_totp || data.requires_2fa || data.mfa_required);

      if (needsOtp) {
        if (preRaw) {
          setPreAuthToken(preRaw);
          window.sessionStorage.setItem("qs_pre_auth_token", preRaw);
          window.sessionStorage.setItem("qs_pre_auth", preRaw);
        }
        if (!preRaw && !forceOTPTest) {
          setError("Two-factor is required — no pre-auth token. Try again or contact an administrator.");
          return;
        }
        setStep("otp");
        setUseBackupCode(false);
        setBackupCode("");
        toast.message("Two-factor verification", {
          description: typeof data.message === "string" ? data.message : "Enter the code from your authenticator app.",
        });
        return;
      }

      const token = data.access_token || data.token;
      if (token) {
        persistSessionToken(token, data.expires_in);
      }
      toast.success("Hive open");
      router.replace(nextPath);
      router.refresh();
    } catch {
      setError("Connection error — server unreachable");
    } finally {
      setLoading(false);
    }
  }

  async function handleOTP(code: string): Promise<void> {
    if (otpSubmitLock.current) {
      return;
    }
    const pre =
      preAuthToken ??
      window.sessionStorage.getItem("qs_pre_auth_token") ??
      window.sessionStorage.getItem("qs_pre_auth");
    if (!pre) {
      setError("Session expired — sign in again.");
      setStep("credentials");
      return;
    }
    otpSubmitLock.current = true;
    setLoading(true);
    setError("");
    try {
      const r = await fetch("/api/auth/totp/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          code,
          totp_code: code,
          pre_auth_token: pre,
        }),
        credentials: "include",
      });
      const data = (await r.json()) as LoginUpstreamResponse;

      if (!r.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Invalid code — try again");
        return;
      }

      const token = data.access_token || data.token;
      if (token) {
        persistSessionToken(token, data.expires_in);
      }
      window.sessionStorage.removeItem("qs_pre_auth");
      window.sessionStorage.removeItem("qs_pre_auth_token");
      toast.success("Verified");
      router.replace(nextPath);
      router.refresh();
    } catch {
      setError("Verification failed — try again");
    } finally {
      setLoading(false);
      otpSubmitLock.current = false;
    }
  }

  function resetOtpStep(): void {
    setStep("credentials");
    setError("");
    setPreAuthToken(null);
    setUseBackupCode(false);
    setBackupCode("");
    window.sessionStorage.removeItem("qs_pre_auth");
    window.sessionStorage.removeItem("qs_pre_auth_token");
  }

  const subtitle =
    step === "credentials"
      ? "The hive is ready — enter your nectar key"
      : "Verify two-factor code from your authenticator";

  return (
    <LoginCardShell subtitle={subtitle} step={step === "credentials" ? 1 : 2}>
      {step === "credentials" ? (
        <div className="v4-login-fields">
          <div className="v4-login-field">
            <label htmlFor="qs-login-email" className="v4-login-label">
              Email
            </label>
            <div className="v4-login-input-wrap">
              <Mail className="v4-login-input-icon h-4 w-4" aria-hidden />
              <input
                id="qs-login-email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void handleLogin()}
                placeholder="operator@your-hive.love"
                className="v4-login-input"
              />
            </div>
          </div>

          <div className="v4-login-field">
            <div className="v4-login-label-row">
              <label htmlFor="qs-login-password" className="v4-login-label">
                Password
              </label>
              <button
                type="button"
                className="v4-login-forgot"
                onClick={() =>
                  toast.message("Reset password", {
                    description: "Use Settings → Security after sign-in, or contact an administrator.",
                  })
                }
              >
                Forgot?
              </button>
            </div>
            <div className="v4-login-input-wrap">
              <Lock className="v4-login-input-icon h-4 w-4" aria-hidden />
              <input
                id="qs-login-password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void handleLogin()}
                placeholder="•••••••••••"
                className="v4-login-input v4-login-input--password"
              />
              <button
                type="button"
                className="v4-login-input-toggle"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {error ? <div className="v4-login-error">{error}</div> : null}

          <div className="v4-login-status-row">
            <div className="v4-login-status-online">
              <span className={hiveOnline === false ? "v4-login-pulse-dot v4-login-pulse-dot--offline" : "v4-login-pulse-dot"} />
              {hiveOnline === null ? "Hive check…" : hiveOnline === false ? "Hive offline" : "Hive online"}
            </div>
            <span className="v4-login-status-meta">
              {hiveOnline === false ? "—" : hiveLatencyMs != null ? `12 nodes synced · ${hiveLatencyMs}ms` : "12 nodes synced"}
            </span>
          </div>

          <button type="button" className="v4-login-btn-primary" disabled={loading} onClick={() => void handleLogin()}>
            <span>{loading ? "Entering hive…" : "Continue"}</span>
            <ArrowRight className="h-4 w-4" aria-hidden />
          </button>

          {isDev && allowDevBypass ? (
            <button
              type="button"
              className="v4-login-btn-ghost"
              onClick={() => {
                toast.message("Dev skip", { description: "Prototype only — use real credentials in production." });
                router.replace(nextPath);
              }}
            >
              Skip 2FA (dev)
            </button>
          ) : null}
        </div>
      ) : (
        <div className="v4-login-fields">
          <div className="v4-login-totp-kicker">
            <Shield className="h-4 w-4" aria-hidden />
            TOTP · Authenticator
          </div>

          {useBackupCode ? (
            <>
              <input
                type="text"
                value={backupCode}
                onChange={(e) => setBackupCode(e.target.value.toUpperCase())}
                placeholder="XXXX-XXXX"
                className="v4-login-backup-input"
                autoComplete="one-time-code"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && backupCode.trim().length >= 8) {
                    void handleOTP(backupCode.replace(/\s+/g, ""));
                  }
                }}
              />
              <button type="button" className="v4-login-backup-link" onClick={() => setUseBackupCode(false)}>
                Use authenticator code instead
              </button>
            </>
          ) : (
            <>
              <LoginOtpInput disabled={loading} onComplete={(code) => void handleOTP(code)} />
              <button type="button" className="v4-login-backup-link" onClick={() => setUseBackupCode(true)}>
                Use a backup code instead
              </button>
            </>
          )}

          {error ? <div className="v4-login-error">{error}</div> : null}

          {loading ? <p className="mb-3 text-center font-mono text-xs text-pollen">Verifying…</p> : null}

          <button
            type="button"
            className="v4-login-btn-primary"
            disabled={loading || (useBackupCode && backupCode.trim().length < 8)}
            onClick={() => {
              if (useBackupCode) {
                void handleOTP(backupCode.replace(/\s+/g, ""));
              }
            }}
          >
            <span>{loading ? "Verifying…" : "Enter the hive"}</span>
            <ArrowRight className="h-4 w-4" aria-hidden />
          </button>

          <button type="button" className="v4-login-btn-ghost" disabled={loading} onClick={resetOtpStep}>
            Back
          </button>
        </div>
      )}
    </LoginCardShell>
  );
}

export default function LoginPage(): JSX.Element {
  return (
    <Suspense
      fallback={
        <div className="font-[family-name:var(--font-space-grotesk)] text-sm text-(--qs-text-3)">Loading hive gate…</div>
      }
    >
      <LoginFormInner />
    </Suspense>
  );
}
