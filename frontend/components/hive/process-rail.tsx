"use client";

import { memo } from "react";

import { cn } from "@/lib/utils";

export type ProcessStepId = "setup" | "plan" | "work" | "verify" | "learn" | "done";

export interface ProcessStep {
  id: ProcessStepId;
  label: string;
  short_label: string;
}

interface ProcessRailProps {
  steps: ProcessStep[];
  currentStep: ProcessStepId;
  compact?: boolean;
}

function ProcessRailInner({ steps, currentStep, compact = false }: ProcessRailProps): JSX.Element {
  const currentIndex = steps.findIndex((step) => step.id === currentStep);

  return (
    <nav
      aria-label="Operator process"
      className={cn(
        "rounded-xl border border-(--qs-border)/60 bg-black/20",
        compact ? "px-3 py-2" : "px-4 py-3",
      )}
    >
      <div className="lg:hidden">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-(--qs-text-3)">
          Step {Math.max(currentIndex + 1, 1)} of {steps.length}
        </p>
        <p className="mt-0.5 text-sm font-semibold text-pollen">
          {steps.find((step) => step.id === currentStep)?.label ?? "Work"}
        </p>
        <div className="mt-2 flex gap-1" aria-hidden>
          {steps.map((step, index) => (
            <span
              key={step.id}
              className={cn(
                "h-1.5 flex-1 rounded-full",
                index <= currentIndex ? "bg-pollen" : "bg-(--qs-border)/50",
              )}
            />
          ))}
        </div>
      </div>

      <ol className="hidden flex-wrap items-center gap-1 lg:flex">
        {steps.map((step, index) => {
          const isCurrent = step.id === currentStep;
          const isPast = currentIndex >= 0 && index < currentIndex;
          return (
            <li key={step.id} className="flex items-center gap-1">
              <span
                className={cn(
                  "inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg px-2 text-xs font-semibold",
                  isCurrent && "bg-pollen/15 text-pollen ring-1 ring-pollen/40",
                  isPast && !isCurrent && "text-[#00FF88]",
                  !isCurrent && !isPast && "text-(--qs-text-3)",
                )}
                aria-current={isCurrent ? "step" : undefined}
              >
                <span className="font-mono text-[10px] opacity-70">{index + 1}</span>
                <span className="ml-1">{step.short_label}</span>
              </span>
              {index < steps.length - 1 ? (
                <span className="text-(--qs-text-3)" aria-hidden>
                  →
                </span>
              ) : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export const ProcessRail = memo(ProcessRailInner);
