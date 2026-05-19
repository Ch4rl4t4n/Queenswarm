"use client";

import type { ClipboardEvent, KeyboardEvent } from "react";
import { useCallback, useRef, useState } from "react";

import { isOtpComplete, normalizeOtpDigit, parseOtpPaste } from "@/lib/login-otp-utils";
import { cn } from "@/lib/utils";

interface LoginOtpInputProps {
  onComplete: (code: string) => void;
  disabled?: boolean;
}

export function LoginOtpInput({ onComplete, disabled }: LoginOtpInputProps) {
  const [digits, setDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const refs = useRef<(HTMLInputElement | null)[]>([]);

  const setRef = useCallback((idx: number, el: HTMLInputElement | null) => {
    refs.current[idx] = el;
  }, []);

  function tryComplete(next: string[]): void {
    if (isOtpComplete(next)) {
      onComplete(next.join(""));
    }
  }

  function handleChange(index: number, value: string): void {
    const clean = normalizeOtpDigit(value);
    const next = [...digits];
    next[index] = clean;
    setDigits(next);
    if (clean && index < 5) {
      refs.current[index + 1]?.focus();
    }
    tryComplete(next);
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
    const next = parseOtpPaste(ev.clipboardData.getData("text"));
    if (!next.some(Boolean)) {
      return;
    }
    setDigits(next);
    refs.current[Math.min(next.filter(Boolean).length, 5)]?.focus();
    tryComplete(next);
  }

  return (
    <div className="v4-login-otp-row">
      {digits.map((d, i) => (
        <input
          key={i}
          ref={(el) => setRef(i, el)}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={d}
          disabled={disabled}
          autoComplete={i === 0 ? "one-time-code" : "off"}
          onChange={(e) => handleChange(i, e.target.value)}
          onKeyDown={(e) => handleKeyDown(i, e)}
          onPaste={handlePaste}
          onFocus={(e) => e.target.select()}
          autoFocus={i === 0}
          aria-label={`Digit ${String(i + 1)}`}
          className={cn("v4-login-otp-cell", d && "v4-login-otp-cell--filled")}
        />
      ))}
    </div>
  );
}
