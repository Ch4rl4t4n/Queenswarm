"use client";

import type { ReactNode } from "react";

import { QueenHoneycombLogo } from "@/components/auth/queen-honeycomb-logo";
import { cn } from "@/lib/utils";

const TERMS_URL = process.env.NEXT_PUBLIC_TERMS_URL ?? "/terms";
const PRIVACY_URL = process.env.NEXT_PUBLIC_PRIVACY_URL ?? "/privacy";

interface LoginCardShellProps {
  children: ReactNode;
  subtitle: string;
  step: 1 | 2;
  className?: string;
}

export function LoginStepper({ step }: { step: 1 | 2 }) {
  return (
    <div className="v4-login-stepper" aria-label={`Login step ${step} of 2`}>
      <span className={cn("v4-login-step-dot", step >= 1 && (step > 1 ? "v4-login-step-dot--done" : "v4-login-step-dot--active"))} />
      <span className={cn("v4-login-step-dot", step >= 2 && "v4-login-step-dot--active")} />
    </div>
  );
}

export function LoginCardFooter() {
  const termsExternal = TERMS_URL.startsWith("http");
  const privacyExternal = PRIVACY_URL.startsWith("http");
  return (
    <p className="v4-login-footer">
      By continuing you agree to our{" "}
      <a
        href={TERMS_URL}
        className="v4-login-footer-link"
        {...(termsExternal ? { target: "_blank", rel: "noopener noreferrer" } : {})}
      >
        Terms
      </a>
      {" · "}
      <a
        href={PRIVACY_URL}
        className="v4-login-footer-link"
        {...(privacyExternal ? { target: "_blank", rel: "noopener noreferrer" } : {})}
      >
        Privacy Policy
      </a>
    </p>
  );
}

/** Glass login card — Hive Control V4 (design-reference LoginScreen). */
export function LoginCardShell({ children, subtitle, step, className }: LoginCardShellProps) {
  return (
    <div className={cn("v4-login-card", className)}>
      <div className="v4-login-brand">
        <QueenHoneycombLogo size={68} />
        <h1 className="v4-login-title">Queenswarm</h1>
        <p className="v4-login-subtitle">{subtitle}</p>
      </div>
      <LoginStepper step={step} />
      {children}
      <LoginCardFooter />
    </div>
  );
}
