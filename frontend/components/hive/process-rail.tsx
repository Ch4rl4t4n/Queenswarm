"use client";

import { memo } from "react";

import { cn } from "@/lib/utils";

/** Mission Control's canonical step ids. Other sections pass their own ids. */
export type ProcessStepId = "setup" | "plan" | "work" | "verify" | "learn" | "done";

export interface ProcessStep<Id extends string = ProcessStepId> {
  id: Id;
  label: string;
  short_label: string;
}

interface ProcessRailProps<Id extends string = ProcessStepId> {
  steps: ProcessStep<Id>[];
  currentStep: Id;
  compact?: boolean;
  /** When provided, each step becomes a button that scrolls to its panel anchor. */
  onSelectStep?: (id: Id) => void;
}

function ProcessRailInner<Id extends string = ProcessStepId>({
  steps,
  currentStep,
  compact = false,
  onSelectStep,
}: ProcessRailProps<Id>): JSX.Element {
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
        {onSelectStep ? (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {steps.map((step, index) => (
              <button
                key={step.id}
                type="button"
                onClick={() => onSelectStep(step.id)}
                className={cn(
                  "min-h-[36px] rounded-lg px-2.5 text-[11px] font-semibold",
                  index <= currentIndex
                    ? "bg-pollen/15 text-pollen"
                    : "border border-(--qs-border)/50 text-(--qs-text-3)",
                )}
                aria-current={step.id === currentStep ? "step" : undefined}
              >
                <span className="font-mono text-[10px] opacity-70">{index + 1}</span>
                <span className="ml-1">{step.short_label}</span>
              </button>
            ))}
          </div>
        ) : (
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
        )}
      </div>

      <ol className="hidden flex-wrap items-center gap-1 lg:flex">
        {steps.map((step, index) => {
          const isCurrent = step.id === currentStep;
          const isPast = currentIndex >= 0 && index < currentIndex;
          const stepClass = cn(
            "inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg px-2 text-xs font-semibold",
            isCurrent && "bg-pollen/15 text-pollen ring-1 ring-pollen/40",
            isPast && !isCurrent && "text-[#00FF88]",
            !isCurrent && !isPast && "text-(--qs-text-3)",
            onSelectStep && "transition hover:bg-pollen/10 hover:text-pollen",
          );
          return (
            <li key={step.id} className="flex items-center gap-1">
              {onSelectStep ? (
                <button
                  type="button"
                  onClick={() => onSelectStep(step.id)}
                  className={stepClass}
                  aria-current={isCurrent ? "step" : undefined}
                >
                  <span className="font-mono text-[10px] opacity-70">{index + 1}</span>
                  <span className="ml-1">{step.short_label}</span>
                </button>
              ) : (
                <span className={stepClass} aria-current={isCurrent ? "step" : undefined}>
                  <span className="font-mono text-[10px] opacity-70">{index + 1}</span>
                  <span className="ml-1">{step.short_label}</span>
                </span>
              )}
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

export const ProcessRail = memo(ProcessRailInner) as typeof ProcessRailInner;
