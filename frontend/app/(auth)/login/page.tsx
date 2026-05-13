"use client";

import type { ClipboardEvent, CSSProperties, KeyboardEvent } from "react";
import { Suspense, useCallback, useEffect, useId, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { QueenHoneycombLogo } from "@/components/auth/queen-honeycomb-logo";
import { cn } from "@/lib/utils";

type LoginStep = "credentials" | "otp";

interface OTPInputProps {
  onComplete: (code: string) => void;
}

function OTPInput({ onComplete }: OTPInputProps): JSX.Element {
  const [digits, setDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const refs = useRef<(HTMLInputElement | null)[]>([]);

  const setRef = useCallback((idx: number, el: HTMLInputElement | null) => {
    refs.current[idx] = el;
  }, []);

  function handleChange(index: number, value: string): void {
    const clean = value.replace(/\D/g, "").slice(-1);
    const next = [...digits];
    next[index] = clean;
    setDigits(next);
    if (clean && index < 5) {
      refs.current[index + 1]?.focus();
    }
    if (next.every((d) => d !== "")) {
      onComplete(next.join(""));
    }
  }

  function handleKeyDown(index: number, ev: KeyboardEvent<HTMLInputElement>): void {
    if (ev.key === "Backspace" && !digits[index] && index > 0) {
      refs.current[index - 1]?.focus();
    }
    if (ev.key === "ArrowLeft" && index > 0) {
      refs.current[index - 1]?.focus();
    }
    if (ev.key === "ArrowRight" && index < 5) {
      refs.current[index + 1]?.focus();
    }
  }

  function handlePaste(ev: ClipboardEvent<HTMLInputElement>): void {
    ev.preventDefault();
    const text = ev.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (!text) {
      return;
    }
    const next = Array.from({ length: 6 }, (_, i) => text[i] ?? "");
    setDigits(next);
    const focusIdx = Math.min(text.length, 5);
    refs.current[focusIdx]?.focus();
    if (next.every((d) => d !== "")) {
      onComplete(next.join(""));
    }
  }

  function boxStyle(filled: boolean): CSSProperties {
    return {
      width: 50,
      height: 60,
      background: "#0a0a0f",
      border: `2px solid ${filled ? "#FFB800" : "#1e1e35"}`,
      borderRadius: 12,
      color: "#e8e8f0",
      fontSize: 26,
      fontWeight: 700,
      fontFamily: "var(--font-hive-mono), ui-monospace, monospace",
      textAlign: "center",
      outline: "none",
      caretColor: "#FFB800",
      transition: "border-color 0.15s",
    };
  }

  return (
    <div style={{ display: "flex", gap: 8, justifyContent: "center", margin: "24px 0" }}>
      {digits.map((d, i) => (
        <input
          key={i}
          ref={(el) => setRef(i, el)}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={d}
          autoComplete={i === 0 ? "one-time-code" : "off"}
          onChange={(e) => handleChange(i, e.target.value)}
          onKeyDown={(e) => handleKeyDown(i, e)}
          onPaste={handlePaste}
          onFocus={(e) => e.target.select()}
          style={boxStyle(d !== "")}
          autoFocus={i === 0}
          aria-label={`Digit ${String(i + 1)}`}
        />
      ))}
    </div>
  );
}

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

function LoginFormInner(): JSX.Element {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath =
    searchParams.get("next") && searchParams.get("next")!.startsWith("/") ? searchParams.get("next")! : "/";
  const forceOTPTest = searchParams.get("test_2fa") === "1";

  const [step, setStep] = useState<LoginStep>("credentials");
  const [email, setEmail] = useState("queen@queenswarm.love");
  const [password, setPassword] = useState("");
  const [preAuthToken, setPreAuthToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hiveOnline, setHiveOnline] = useState<boolean | null>(null);
  const bgPatternId = useId();
  const hexPatA = `login-hx-${bgPatternId}`;
  const hexPatB = `login-hx2-${bgPatternId}`;
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
    let alive = true;
    void (async () => {
      try {
        const res = await fetch("/health", { cache: "no-store" });
        if (alive) {
          setHiveOnline(res.ok);
        }
      } catch {
        if (alive) {
          setHiveOnline(false);
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
        setLoading(false);
        return;
      }

      if (forceOTPTest) {
        setStep("otp");
        setLoading(false);
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
          if (typeof window !== "undefined") {
            window.sessionStorage.setItem("qs_pre_auth_token", preRaw);
            window.sessionStorage.setItem("qs_pre_auth", preRaw);
          }
        }
        if (!preRaw && !forceOTPTest) {
          setError("Two-factor is required — no pre-auth token. Try again or contact an administrator.");
          setLoading(false);
          return;
        }
        setStep("otp");
        setLoading(false);
        toast.message("Two-factor verification", {
          description: typeof data.message === "string" ? data.message : "Enter the code from your authenticator app.",
        });
        return;
      }

      const token = data.access_token || data.token;
      if (token) {
        const maxAgeRaw = typeof data.expires_in === "number" ? data.expires_in : 1800;
        const maxAge = Math.max(120, maxAgeRaw);
        if (typeof window !== "undefined") {
          localStorage.setItem("qs_token", token.trim());
          const secure = window.location.protocol === "https:" ? "; Secure" : "";
          document.cookie = `qs_token=${encodeURIComponent(token.trim())}; Path=/; Max-Age=${String(maxAge)}; SameSite=Lax${secure}`;
        }
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
      (typeof window !== "undefined"
        ? window.sessionStorage.getItem("qs_pre_auth_token") ??
          window.sessionStorage.getItem("qs_pre_auth")
        : null);
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
      const data = (await r.json()) as LoginUpstreamResponse & { access_token?: string; expires_in?: number };

      if (!r.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Invalid code — try again");
        return;
      }

      const token = data.access_token || data.token;
      if (token && typeof window !== "undefined") {
        localStorage.setItem("qs_token", token.trim());
        const maxAgeRaw = typeof data.expires_in === "number" ? data.expires_in : 1800;
        const maxAge = Math.max(120, maxAgeRaw);
        const secure = window.location.protocol === "https:" ? "; Secure" : "";
        document.cookie = `qs_token=${encodeURIComponent(token.trim())}; Path=/; Max-Age=${String(maxAge)}; SameSite=Lax${secure}`;
      }
      if (typeof window !== "undefined") {
        window.sessionStorage.removeItem("qs_pre_auth");
        window.sessionStorage.removeItem("qs_pre_auth_token");
      }
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

  const inputStyle: CSSProperties = {
    width: "100%",
    padding: "12px 14px",
    background: "#0a0a0f",
    border: "1px solid #1e1e35",
    borderRadius: 10,
    color: "#e8e8f0",
    fontSize: 14,
    fontFamily: "var(--font-hive-mono), ui-monospace, monospace",
    outline: "none",
    transition: "border-color 0.15s",
    boxSizing: "border-box",
  };

  return (
    <div
      className="fixed inset-0 z-[20] overflow-y-auto"
      style={{
        minHeight: "100vh",
        background: "#09090f",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 20,
      }}
    >
      <svg
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.04, pointerEvents: "none" }}
        aria-hidden
      >
        <defs>
          <pattern id={hexPatA} x="0" y="0" width="60" height="69" patternUnits="userSpaceOnUse">
            <polygon points="30,0 60,17 60,52 30,69 0,52 0,17" fill="none" stroke="#FFB800" strokeWidth="1" />
          </pattern>
          <pattern id={hexPatB} x="30" y="34.5" width="60" height="69" patternUnits="userSpaceOnUse">
            <polygon points="30,0 60,17 60,52 30,69 0,52 0,17" fill="none" stroke="#FFB800" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill={`url(#${hexPatA})`} />
        <rect width="100%" height="100%" fill={`url(#${hexPatB})`} />
      </svg>

      <div
        style={{
          position: "absolute",
          top: "20%",
          left: "50%",
          transform: "translateX(-50%)",
          width: 500,
          height: 500,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(255,184,0,0.05) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />

      <div
        style={{
          position: "relative",
          zIndex: 1,
          width: "100%",
          maxWidth: 420,
          background: "rgba(13,13,35,0.92)",
          border: "1px solid rgba(255,184,0,0.18)",
          borderRadius: 20,
          padding: "40px 36px",
          boxShadow: "0 24px 64px rgba(0,0,0,0.6)",
          backdropFilter: "blur(20px)",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginBottom: 32 }}>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: 20, overflow: "visible" }}>
            <QueenHoneycombLogo size={80} />
          </div>
          <div
            style={{
              marginTop: 14,
              fontSize: 22,
              fontWeight: 700,
              color: "#e8e8f0",
              fontFamily: "'Poppins', sans-serif",
              letterSpacing: "-0.3px",
            }}
          >
            Queenswarm
          </div>
        </div>

        {step === "credentials" && (
          <>
            <div style={{ marginBottom: 24 }}>
              <div
                style={{
                  fontSize: 18,
                  fontWeight: 600,
                  color: "#e8e8f0",
                  marginBottom: 4,
                  fontFamily: "'Poppins', sans-serif",
                }}
              >
                Welcome back
              </div>
              <div style={{ fontSize: 13, color: "#5a5a7a" }}>Enter your hive credentials</div>
            </div>

            <div style={{ marginBottom: 14 }}>
              <label
                htmlFor="qs-login-email"
                style={{
                  display: "block",
                  fontSize: 10,
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                  color: "#5a5a7a",
                  marginBottom: 6,
                }}
              >
                Email
              </label>
              <input
                id="qs-login-email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void handleLogin()}
                style={inputStyle}
                onFocus={(e) => {
                  e.target.style.borderColor = "#FFB800";
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = "#1e1e35";
                }}
              />
            </div>

            <div style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <label
                  htmlFor="qs-login-password"
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.1em",
                    color: "#5a5a7a",
                  }}
                >
                  Password
                </label>
                <button
                  type="button"
                  style={{ fontSize: 12, color: "#FFB800", textDecoration: "none", background: "none", border: "none", cursor: "pointer", padding: 0 }}
                  onClick={() =>
                    toast.message("Reset password", {
                      description: "Use the security settings in the hive or contact an administrator.",
                    })
                  }
                >
                  Forgot?
                </button>
              </div>
              <input
                id="qs-login-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void handleLogin()}
                placeholder="••••••••••••"
                style={inputStyle}
                onFocus={(e) => {
                  e.target.style.borderColor = "#FFB800";
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = "#1e1e35";
                }}
              />
            </div>

            {error ? (
              <div
                style={{
                  marginBottom: 14,
                  padding: "10px 14px",
                  background: "rgba(255,51,102,0.08)",
                  border: "1px solid rgba(255,51,102,0.3)",
                  borderRadius: 8,
                  color: "#FF3366",
                  fontSize: 13,
                  fontFamily: "var(--font-hive-mono), ui-monospace, monospace",
                }}
              >
                {error}
              </div>
            ) : null}

            <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 18 }}>
              <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, fontFamily: "var(--font-hive-mono), monospace", color: "#00FF88" }}>
                <span
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: "50%",
                    background: hiveOnline === false ? "#FF3366" : "#00FF88",
                    boxShadow: hiveOnline === false ? "none" : "0 0 6px #00FF88",
                    animation: hiveOnline === true ? "qs-pulse 2s ease-in-out infinite" : "none",
                    display: "inline-block",
                  }}
                />
                {hiveOnline === null ? "Hive check…" : hiveOnline === false ? "HIVE OFFLINE" : "HIVE ONLINE"}
              </span>
            </div>

            <button
              type="button"
              onClick={() => void handleLogin()}
              disabled={loading}
              className={cn("qs-btn qs-btn--primary qs-btn--xl qs-btn--full")}
            >
              {loading ? "Entering hive..." : "CONTINUE →"}
            </button>
          </>
        )}

        {step === "otp" && (
          <div style={{ textAlign: "center" }}>
            <button
              type="button"
              onClick={() => {
                setStep("credentials");
                setError("");
                setPreAuthToken(null);
                if (typeof window !== "undefined") {
                  window.sessionStorage.removeItem("qs_pre_auth");
                  window.sessionStorage.removeItem("qs_pre_auth_token");
                }
              }}
              style={{
                background: "none",
                border: "none",
                color: "#5a5a7a",
                fontSize: 12,
                cursor: "pointer",
                marginBottom: 20,
                display: "flex",
                alignItems: "center",
                gap: 4,
                margin: "0 auto 20px",
                fontFamily: "var(--font-hive-mono), ui-monospace, monospace",
              }}
            >
              ← Back
            </button>

            <div
              style={{
                fontSize: 17,
                fontWeight: 700,
                color: "#e8e8f0",
                marginBottom: 6,
                fontFamily: "'Poppins', sans-serif",
              }}
            >
              Two-factor verification
            </div>
            <div style={{ fontSize: 13, color: "#5a5a7a", lineHeight: 1.6, marginBottom: 4 }}>Open Google Authenticator</div>
            <div style={{ fontSize: 12, color: "#5a5a7a", lineHeight: 1.55, marginBottom: 12 }}>
              Enter the 6-digit code for <strong style={{ color: "#9898b8" }}>Queenswarm</strong>
            </div>
            <p style={{ fontSize: 11, color: "#4a4a6a", lineHeight: 1.55, marginBottom: 14, maxWidth: 360, marginInline: "auto" }}>
              Zobrazí sa len vtedy, keď už máš 2FA aktivovaný. Nie je spárovaný telefón? Skús{" "}
              <strong style={{ color: "#6a6a8a" }}>záložný kód</strong> alebo obráť sa na administrátora. Ak 2FA ešte nemáš
              nastavený, choď ← Späť a po prihlásení ho dokončíš v časti{" "}
              <strong style={{ color: "#6a6a8a" }}>Nastavenia → Security</strong>.
            </p>

            <OTPInput onComplete={(code) => void handleOTP(code)} />

            {error ? (
              <div
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  marginTop: 8,
                  background: "rgba(255,51,102,0.08)",
                  border: "1px solid rgba(255,51,102,0.3)",
                  color: "#FF3366",
                  fontSize: 13,
                  fontFamily: "var(--font-hive-mono), ui-monospace, monospace",
                }}
              >
                {error}
              </div>
            ) : null}

            {loading ? (
              <div style={{ color: "#FFB800", fontSize: 13, fontFamily: "var(--font-hive-mono), monospace", marginTop: 12 }}>
                Verifying...
              </div>
            ) : null}
          </div>
        )}

        <p style={{ textAlign: "center", color: "#3a3a5a", fontSize: 11, marginTop: 24, marginBottom: 0 }}>
          By continuing you agree to our{" "}
          <button
            type="button"
            style={{ color: "#5a5a7a", textDecoration: "none", background: "none", border: "none", cursor: "pointer", padding: 0 }}
            onClick={() => toast.message("Terms", { description: "Legal copy ships with GA — placeholder control." })}
          >
            Terms
          </button>
          {" · "}
          <button
            type="button"
            style={{ color: "#5a5a7a", textDecoration: "none", background: "none", border: "none", cursor: "pointer", padding: 0 }}
            onClick={() => toast.message("Privacy", { description: "Placeholder — link site policy when published." })}
          >
            Privacy Policy
          </button>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage(): JSX.Element {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[40vh] w-full items-center justify-center font-[family-name:var(--font-jetbrains-mono)] text-sm text-zinc-500">
          Loading hive gate…
        </div>
      }
    >
      <LoginFormInner />
    </Suspense>
  );
}
