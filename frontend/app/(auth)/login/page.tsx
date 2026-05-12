"use client";

import { ArrowRightIcon } from "lucide-react";
import type { FormEvent } from "react";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { AuthHexLogo } from "@/components/auth/auth-hex-logo";
import { cn } from "@/lib/utils";

const SHOW_LOGIN_SSO = process.env.NEXT_PUBLIC_LOGIN_SSO_ENABLED === "true";

interface LoginUpstreamResponse {
  ok?: boolean;
  requires_totp?: boolean;
  pre_auth_token?: string | null;
  detail?: string;
  access_token?: string;
}

function RememberToggle({
  checked,
  onChange,
  id,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  id: string;
}) {
  return (
    <button
      type="button"
      id={id}
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative h-6 w-10 shrink-0 rounded-full border transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pollen/50",
        checked ? "border-pollen bg-pollen" : "border-[#2a2a5e] bg-[#1a1a3e]",
      )}
    >
      <span
        className={cn(
          "absolute top-0.5 h-5 w-5 rounded-full shadow-sm transition-all duration-200",
          checked ? "left-[calc(100%-1.375rem)] bg-black" : "left-0.5 bg-[#4a4a7e]",
        )}
        aria-hidden
      />
    </button>
  );
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath =
    searchParams.get("next") && searchParams.get("next")!.startsWith("/") ? searchParams.get("next")! : "/";

  const [email, setEmail] = useState("queen@queenswarm.love");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [hiveOnline, setHiveOnline] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

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

  async function submit(ev: FormEvent<HTMLFormElement>): Promise<void> {
    ev.preventDefault();
    setError("");
    if (!password.trim()) {
      setError("Enter your password.");
      return;
    }
    setBusy(true);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = (await res.json()) as LoginUpstreamResponse;
      if (!res.ok) {
        const msg = typeof data.detail === "string" ? data.detail : "Prihlásenie zlyhalo.";
        setError(msg);
        toast.error(msg);
        return;
      }
      if (data.requires_totp) {
        if (typeof window !== "undefined" && typeof data.pre_auth_token === "string") {
          window.sessionStorage.setItem("qs_pre_auth", data.pre_auth_token);
        }
        toast.message("Dvojstupňové overenie", { description: "Zadaj TOTP z aplikácie." });
        router.push(`/verify-2fa?next=${encodeURIComponent(nextPath)}`);
        router.refresh();
        return;
      }
      if (rememberMe) {
        localStorage.setItem("qs_login_remember", "1");
      } else {
        localStorage.removeItem("qs_login_remember");
      }
      if (typeof window !== "undefined" && typeof data.access_token === "string" && data.access_token.trim()) {
        localStorage.setItem("qs_token", data.access_token.trim());
      }
      toast.success("Hive open");
      router.push(nextPath);
      router.refresh();
    } catch {
      const msg = "Connection error — check server.";
      setError(msg);
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  function hintSso(which: string): void {
    toast.message("Čoskoro", { description: `${which} SSO ešte pripojíme.` });
  }

  return (
    <div className="relative mx-auto w-full max-w-[440px] rounded-2xl border border-pollen/20 bg-[#0d0d2b]/85 p-8 shadow-[0_0_60px_rgb(255_184_0/0.06),0_25px_50px_rgba(0,0,0,0.5)] backdrop-blur-xl">
      <div aria-hidden className="pointer-events-none absolute -right-16 -top-12 h-36 w-36 rounded-full bg-pollen/10 blur-3xl" />

      <div className="mb-8 flex flex-col items-center text-center">
        <div className="mb-4 h-16 w-16 drop-shadow-[0_0_24px_rgba(255,184,0,0.35)]">
          <AuthHexLogo />
        </div>
        <p className="font-[family-name:var(--font-space-grotesk)] text-2xl font-bold tracking-tight text-[#fafafa]">
          Queenswarm
        </p>
        <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
          100+ autonomous agents · 24/7
        </p>
      </div>

      <div className="mb-6">
        <h1 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">
          Welcome back
        </h1>
        <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
          Enter your hive credentials
        </p>
      </div>

      {SHOW_LOGIN_SSO ? (
        <>
          <button
            type="button"
            onClick={() => hintSso("Google")}
            className="mb-3 flex w-full items-center justify-center gap-3 rounded-xl border border-cyan/20 bg-black/35 py-3 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] transition hover:border-pollen/30"
          >
            <span className="font-semibold tracking-tight">G</span> Continue with Google
          </button>
          <button
            type="button"
            onClick={() => hintSso("Discord")}
            className="mb-6 flex w-full items-center justify-center gap-3 rounded-xl border border-cyan/20 bg-black/35 py-3 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] transition hover:border-pollen/35"
          >
            <span className="rounded bg-[#5865f2]/90 px-1.5 py-0.5 text-[10px] font-bold text-white">D</span>
            Continue with Discord
          </button>
          <div className="mb-6 flex items-center gap-3 font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.28em] text-zinc-500">
            <span className="h-px flex-1 bg-cyan/15" aria-hidden /> or hive id{" "}
            <span className="h-px flex-1 bg-cyan/15" aria-hidden />
          </div>
        </>
      ) : null}

      <form onSubmit={(ev) => void submit(ev)} className="space-y-5">
        <label className="block space-y-2" htmlFor="login-email">
          <span className="font-[family-name:var(--font-inter)] text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500">
            Email
          </span>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-xl border border-[#1a1a3e] bg-[#080818] px-4 py-3 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] outline-none ring-0 transition placeholder:text-zinc-600 focus:border-pollen focus:shadow-[0_0_22px_rgb(255_184_0/0.22)] focus:outline-none focus:ring-2 focus:ring-pollen/25"
            placeholder="queen@queenswarm.love"
          />
        </label>

        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <label
              htmlFor="login-password"
              className="font-[family-name:var(--font-inter)] text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500"
            >
              Password
            </label>
            <button
              type="button"
              className="font-[family-name:var(--font-inter)] text-xs font-medium text-pollen hover:underline"
              onClick={() =>
                toast.message("Reset password", {
                  description: "Spustíme hive reset flow čoskoro — použite admin konzolu alebo support.",
                })
              }
            >
              Forgot?
            </button>
          </div>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-xl border border-[#1a1a3e] bg-[#080818] px-4 py-3 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] outline-none transition placeholder:text-zinc-600 focus:border-pollen focus:shadow-[0_0_22px_rgb(255_184_0/0.22)] focus:outline-none focus:ring-2 focus:ring-pollen/25"
            placeholder="••••••••"
          />
        </div>

        {error ? (
          <div
            role="alert"
            className="rounded-lg border border-danger/40 bg-danger/10 px-4 py-2.5 font-[family-name:var(--font-jetbrains-mono)] text-sm text-danger"
          >
            {error}
          </div>
        ) : null}

        <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
          <div className="flex items-center gap-2.5">
            <RememberToggle checked={rememberMe} onChange={setRememberMe} id="remember-toggle" />
            <label htmlFor="remember-toggle" className="cursor-pointer select-none text-sm text-zinc-400">
              Remember me
            </label>
          </div>
          <span className="inline-flex items-center gap-2 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-success">
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                hiveOnline === true && "animate-pulse shadow-[0_0_6px_#00FF88]",
                hiveOnline === true && "bg-success",
                hiveOnline === false && "bg-alert",
                hiveOnline === null && "bg-zinc-500",
              )}
            />
            {hiveOnline === null ? "Checking…" : hiveOnline === false ? "Hive offline" : "Hive online"}
          </span>
        </div>

        <button
          type="submit"
          disabled={busy}
          className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl border border-pollen bg-pollen py-3.5 font-[family-name:var(--font-space-grotesk)] text-sm font-bold uppercase tracking-[0.06em] text-black shadow-[0_0_30px_rgb(255_184_0/0.33)] transition hover:bg-[#ffc933] disabled:cursor-not-allowed disabled:border-pollen/70 disabled:bg-pollen/80 disabled:shadow-none"
        >
          {busy ? (
            <>Entering hive…</>
          ) : (
            <>
              Continue <ArrowRightIcon className="h-5 w-5" aria-hidden />
            </>
          )}
        </button>
      </form>

      <p className="mt-6 text-center font-[family-name:var(--font-inter)] text-xs leading-relaxed text-zinc-600">
        By continuing you agree to our{" "}
        <button type="button" className="text-zinc-500 underline-offset-4 hover:text-zinc-300 hover:underline" onClick={() => hintSso("Terms")}>
          Terms
        </button>{" "}
        ·{" "}
        <button
          type="button"
          className="text-zinc-500 underline-offset-4 hover:text-zinc-300 hover:underline"
          onClick={() => hintSso("Privacy")}
        >
          Privacy Policy
        </button>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto flex min-h-[360px] w-full max-w-md items-center justify-center rounded-2xl border border-pollen/15 bg-[#0d0d2b]/60 text-zinc-500 backdrop-blur">
          Loading hive gate…
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
