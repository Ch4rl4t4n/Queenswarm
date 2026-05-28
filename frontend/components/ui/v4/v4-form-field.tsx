import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface V4FormFieldProps {
  /** Uppercase kicker label — use `v4-field-label` styling. */
  label: string;
  htmlFor?: string;
  children: ReactNode;
  className?: string;
  /** Optional helper row below the control (badges, hints). */
  footer?: ReactNode;
}

/** Single label + control — 6px label gap (`v4-form-field`). */
export function V4FormField({ label, htmlFor, children, className, footer }: V4FormFieldProps) {
  return (
    <div className={cn("v4-form-field", className)}>
      <label htmlFor={htmlFor} className="v4-field-label">
        {label}
      </label>
      {children}
      {footer ? <div className="v4-form-field-footer">{footer}</div> : null}
    </div>
  );
}

interface V4FormStackProps {
  children: ReactNode;
  className?: string;
}

/** Vertical stack of form fields — 16px between fields (`v4-form-stack`). */
export function V4FormStack({ children, className }: V4FormStackProps) {
  return <div className={cn("v4-form-stack", className)}>{children}</div>;
}
