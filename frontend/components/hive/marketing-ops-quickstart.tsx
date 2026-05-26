"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, BookOpen, Loader2, Mail, Play, Sparkles } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { V4Card } from "@/components/ui/v4";
import { startFirstRunSession } from "@/lib/virtual-company-api";

export interface MarketingOpsQuickstartProps {
  swarmId: string;
}

const STEPS = [
  {
    icon: BookOpen,
    title: "Connect Notion OAuth",
    detail: "Integrations → Execution Studio → Connect Notion. Required for simulate publish.",
    href: "/integrations?tab=studio",
  },
  {
    icon: Mail,
    title: "Connect Gmail (optional)",
    detail: "Enables outreach drafts — still simulate-first until you approve live.",
    href: "/integrations?tab=studio",
  },
  {
    icon: Sparkles,
    title: "Run supervisor in simulate mode",
    detail: "One-click starts a durable session with the Marketing Ops first-run playbook.",
    action: "start_session" as const,
  },
] as const;

/** Post-build guided path for the Marketing Ops department swarm. */
export function MarketingOpsQuickstart({ swarmId }: MarketingOpsQuickstartProps): JSX.Element {
  const router = useRouter();
  const [sessionBusy, setSessionBusy] = useState(false);

  const startSession = async (): Promise<void> => {
    setSessionBusy(true);
    try {
      await startFirstRunSession("marketing-ops");
      toast.success("Simulate session started — open Agents → Sessions");
      router.push("/agents#sessions");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Session start failed");
    } finally {
      setSessionBusy(false);
    }
  };

  return (
    <V4Card className="mt-3 border-pollen/25 bg-pollen/5">
      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-pollen">Marketing Ops · first run</p>
      <p className="mt-1 text-xs text-(--qs-text-3)">
        Swarm <span className="font-mono text-(--qs-cyan)">{swarmId.slice(0, 8)}…</span> is ready. Complete these
        steps before live writes.
      </p>
      <ol className="mt-3 space-y-2">
        {STEPS.map((step, index) => {
          const Icon = step.icon;
          if ("action" in step && step.action === "start_session") {
            return (
              <li key={step.title}>
                <button
                  type="button"
                  disabled={sessionBusy}
                  onClick={() => void startSession()}
                  className="flex w-full items-start gap-3 rounded-lg border border-pollen/35 bg-pollen/10 px-3 py-2 text-left transition hover:border-pollen/55 hover:bg-pollen/15 disabled:opacity-60"
                >
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-pollen/20 font-mono text-[10px] text-pollen">
                    {index + 1}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-1.5 text-sm font-semibold text-(--qs-text)">
                      {sessionBusy ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-pollen" aria-hidden />
                      ) : (
                        <Play className="h-3.5 w-3.5 text-pollen" aria-hidden />
                      )}
                      {step.title}
                    </span>
                    <span className="mt-0.5 block text-xs text-(--qs-text-3)">{step.detail}</span>
                  </span>
                </button>
              </li>
            );
          }
          return (
            <li key={step.title}>
              <Link
                href={"href" in step ? step.href : "/integrations?tab=studio"}
                className="flex items-start gap-3 rounded-lg border border-(--qs-border)/30 bg-black/25 px-3 py-2 transition hover:border-pollen/40 hover:bg-pollen/5"
              >
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-pollen/15 font-mono text-[10px] text-pollen">
                  {index + 1}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-1.5 text-sm font-semibold text-(--qs-text)">
                    <Icon className="h-3.5 w-3.5 text-pollen" aria-hidden />
                    {step.title}
                  </span>
                  <span className="mt-0.5 block text-xs text-(--qs-text-3)">{step.detail}</span>
                </span>
                <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-(--qs-text-3)" aria-hidden />
              </Link>
            </li>
          );
        })}
      </ol>
    </V4Card>
  );
}
