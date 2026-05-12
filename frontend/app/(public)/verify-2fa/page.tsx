"use client";

import type { ClipboardEvent, FormEvent } from "react";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRightIcon, HexagonIcon } from "lucide-react";
import { toast } from "sonner";

import { NeonButton } from "@/components/ui/neon-button";

function VerifyInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = searchParams.get("next") && searchParams.get("next")!.startsWith("/") ? searchParams.get("next")! : "/";

  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(ev: FormEvent<HTMLFormElement>): Promise<void> {
    ev.preventDefault();
    const trimmed = code.replace(/\s+/g, "");
    const pre =
      typeof window !== "undefined" ? window.sessionStorage.getItem("qs_pre_auth") : null;

    if (!pre) {
      toast.error("Žiadny pre-token. Začni znova prihlásením.");
      router.push(`/login?next=${encodeURIComponent(nextPath)}`);
      return;
    }
    setBusy(true);
    try {
      const res = await fetch("/api/auth/verify-2fa", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pre_auth_token: pre, totp_code: trimmed }),
      });
      const data = (await res.json()) as { detail?: string; ok?: boolean; access_token?: string };
      if (!res.ok) {
        toast.error(typeof data.detail === "string" ? data.detail : "Kód zamietnutý.");
        return;
      }
      if (typeof window !== "undefined" && typeof data.access_token === "string" && data.access_token.trim()) {
        localStorage.setItem("qs_token", data.access_token.trim());
      }
      if (typeof window !== "undefined") {
        window.sessionStorage.removeItem("qs_pre_auth");
      }
      toast.success("Overené");
      router.push(nextPath);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  function onPaste(ev: ClipboardEvent<HTMLInputElement>): void {
    const text = ev.clipboardData.getData("text/plain").trim().replace(/\D/g, "");
    if (text.length >= 6) {
      setCode(text.slice(0, 8));
    }
  }

  const slots = [...Array(6)].map((_, i) => {
    const digit = code[i] ?? "";
    const focusNext = code.length === i;
    return (
      <div
        key={`totp-slot-${String(i)}`}
        className={`flex aspect-square w-full max-w-[44px] items-center justify-center rounded-lg border font-[family-name:var(--font-jetbrains-mono)] text-lg text-[#fafafa] ${
          digit || focusNext ? "border-pollen/55 shadow-[0_0_10px_rgb(255_184_0/0.2)]" : "border-cyan/15 bg-black/40"
        }`}
      >
        {digit || (focusNext ? <span className="text-data/40">●</span> : "")}
      </div>
    );
  });

  return (
    <div className="relative mx-auto w-full max-w-[460px] space-y-10 rounded-3xl border border-cyan/[0.15] bg-hive-card/90 p-10 shadow-[0_28px_80px_rgba(0,0,0,0.65)] backdrop-blur-md">
      <div className="flex flex-col items-center gap-8 text-center">
        <HexagonIcon className="h-14 w-14 text-pollen drop-shadow-[0_0_28px_rgb(255_184_0/0.75)]" strokeWidth={1.35} />
        <div>
          <p className="font-[family-name:var(--font-inter)] text-xl font-semibold text-[#fafafa]">
            Hive security checkpoint
          </p>
          <p className="mt-3 max-w-sm font-[family-name:var(--font-inter)] text-sm leading-relaxed text-muted-foreground">
            Enter authenticator digits or backup code issued when TOTP enrolment finalized.
          </p>
          <NeonButton
            type="button"
            variant="ghost"
            className="mt-4 uppercase tracking-[0.2em]"
            onClick={() => router.push("/login")}
          >
            ← BACK TO LOGIN
          </NeonButton>
        </div>
      </div>

      <form onSubmit={(ev) => void submit(ev)} className="space-y-8">
        <div className="relative">
          <label htmlFor="hive-totp" className="sr-only">
            Authenticator code
          </label>
          <div className="mb-6 flex justify-center gap-2 sm:gap-3">{slots}</div>
          <input
            id="hive-totp"
            autoFocus
            inputMode="numeric"
            pattern="[0-9]*"
            autoComplete="one-time-code"
            value={code}
            onPaste={onPaste}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 8))}
            className="w-full rounded-xl border border-cyan/[0.15] bg-black/45 px-4 py-3 text-center font-[family-name:var(--font-jetbrains-mono)] text-lg tracking-[0.85em] text-[#fafafa] focus:border-pollen/45 focus:outline-none focus:ring-2 focus:ring-pollen/25"
          />
        </div>

        <NeonButton
          type="submit"
          variant="primary"
          disabled={busy || code.trim().length < 6}
          className="w-full justify-between py-3.5 text-sm uppercase tracking-[0.24em]"
        >
          VERIFY SESSION
          <ArrowRightIcon className="h-4 w-4" />
        </NeonButton>
      </form>
    </div>
  );
}

export default function Verify2faPage() {
  return (
    <Suspense
      fallback={<div className="text-center font-[family-name:var(--font-jetbrains-mono)] text-sm text-data">Hive gate…</div>}
    >
      <VerifyInner />
    </Suspense>
  );
}
