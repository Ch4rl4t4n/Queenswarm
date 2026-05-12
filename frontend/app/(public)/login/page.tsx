"use client";

import { ArrowRightIcon, HexagonIcon } from "lucide-react";
import type { FormEvent } from "react";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { NeonButton } from "@/components/ui/neon-button";
import { HiveSwitch } from "@/components/ui/hive-switch";
import { StatusIndicator } from "@/components/ui/status-indicator";

const SHOW_LOGIN_SSO = process.env.NEXT_PUBLIC_LOGIN_SSO_ENABLED === "true";

interface LoginUpstreamResponse {
  ok?: boolean;
  requires_totp?: boolean;
  pre_auth_token?: string | null;
  detail?: string;
  access_token?: string;
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = searchParams.get("next") && searchParams.get("next")!.startsWith("/") ? searchParams.get("next")! : "/";

  const [email, setEmail] = useState("queen@queenswarm.love");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [hiveOnline, setHiveOnline] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);

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
        toast.error(typeof data.detail === "string" ? data.detail : "Prihlásenie zlyhalo.");
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
    } finally {
      setBusy(false);
    }
  }

  function hintSso(which: string): void {
    toast.message("Čoskoro", { description: `${which} SSO ešte pripojíme.` });
  }

  return (
    <div className="relative mx-auto w-full max-w-[440px] space-y-7 rounded-[20px] border border-white/[0.08] bg-[#16161d]/95 p-8 shadow-[0_32px_80px_rgba(0,0,0,0.72)] backdrop-blur-md">
      <div aria-hidden className="pointer-events-none absolute -right-20 -top-16 h-40 w-40 rounded-full bg-pollen/12 blur-3xl" />

      {/* Brand row */}
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-pollen/35 bg-pollen/10 shadow-[0_0_28px_rgb(255_184_0/0.35)]">
          <HexagonIcon className="h-7 w-7 text-pollen" strokeWidth={1.35} aria-hidden />
        </div>
        <div>
          <p className="font-[family-name:var(--font-space-grotesk)] text-xl font-bold tracking-tight text-[#fafafa]">
            QueenSwarm
          </p>
          <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-zinc-500">100+ autonomous agents · 24/7</p>
        </div>
      </div>

      <div>
        <h1 className="font-[family-name:var(--font-space-grotesk)] text-2xl font-semibold tracking-tight text-[#fafafa]">
          Welcome back
        </h1>
        <p className="mt-1.5 font-[family-name:var(--font-inter)] text-sm text-zinc-500">Enter your hive credentials</p>
      </div>

      {SHOW_LOGIN_SSO ? (
        <>
          <button
            type="button"
            onClick={() => hintSso("Google")}
            className="flex w-full items-center justify-center gap-3 rounded-xl border border-cyan/20 bg-black/35 py-3 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] transition hover:border-pollen/30"
          >
            <span className="font-semibold tracking-tight">G</span> Continue with Google
          </button>
          <button
            type="button"
            onClick={() => hintSso("Discord")}
            className="flex w-full items-center justify-center gap-3 rounded-xl border border-cyan/20 bg-black/35 py-3 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] transition hover:border-pollen/35"
          >
            <span className="rounded bg-[#5865f2]/90 px-1.5 py-0.5 text-[10px] font-bold text-white">D</span>
            Continue with Discord
          </button>
          <div className="flex items-center gap-3 font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.28em] text-zinc-500">
            <span className="h-px flex-1 bg-cyan/15" aria-hidden /> or hive id <span className="h-px flex-1 bg-cyan/15" aria-hidden />
          </div>
        </>
      ) : null}

      <form onSubmit={(ev) => void submit(ev)} className="space-y-5">
        <label className="block space-y-2">
          <span className="font-[family-name:var(--font-inter)] text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500">
            Email
          </span>
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-xl border border-white/[0.1] bg-[#0d0d12]/90 px-4 py-3 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] placeholder:text-zinc-600 focus:border-pollen/40 focus:outline-none focus:ring-2 focus:ring-pollen/20"
            placeholder="queen@queenswarm.love"
          />
        </label>

        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="font-[family-name:var(--font-inter)] text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500">
              Password
            </span>
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
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-xl border border-white/[0.1] bg-[#0d0d12]/90 px-4 py-3 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] placeholder:text-zinc-600 focus:border-pollen/40 focus:outline-none focus:ring-2 focus:ring-pollen/20"
            placeholder="••••••••"
          />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
          <div className="flex items-center gap-3">
            <HiveSwitch checked={rememberMe} onCheckedChange={setRememberMe} aria-label="Remember me on this device" />
            <span className="font-[family-name:var(--font-inter)] text-sm text-zinc-400">Remember me</span>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-success/40 bg-black/35 px-3 py-1.5 shadow-[inset_0_0_0_1px_rgba(0,255,136,0.12)]">
            <StatusIndicator
              tone={hiveOnline === false ? "idle" : "online"}
              label={hiveOnline === null ? "Checking…" : hiveOnline === false ? "Hive offline" : "Hive online"}
              pulse={hiveOnline === true}
            />
          </div>
        </div>

        <NeonButton
          type="submit"
          variant="primary"
          disabled={busy}
          className="mt-2 w-full border-pollen bg-pollen py-3.5 font-[family-name:var(--font-space-grotesk)] text-base uppercase tracking-[0.08em] text-black shadow-[0_0_36px_rgb(255_184_0/0.52)] hover:bg-[#ffc933]"
        >
          Continue
          <ArrowRightIcon className="h-5 w-5" aria-hidden />
        </NeonButton>
      </form>

      <p className="text-center font-[family-name:var(--font-inter)] text-xs leading-relaxed text-zinc-500">
        By continuing you agree to our{" "}
        <button type="button" className="text-pollen hover:underline" onClick={() => hintSso("Terms")}>
          Terms
        </button>{" "}
        ·{" "}
        <button type="button" className="text-pollen hover:underline" onClick={() => hintSso("Privacy")}>
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
        <div className="mx-auto flex min-h-[360px] w-full max-w-md items-center justify-center rounded-[20px] border border-white/[0.08] bg-[#16161d]/80 text-zinc-500">
          Loading hive gate…
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
