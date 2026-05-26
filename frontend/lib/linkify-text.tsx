"use client";

import type { JSX } from "react";
import { useMemo } from "react";

import { cn } from "@/lib/utils";

const URL_RE = /(https?:\/\/[^\s<]+[^\s<.,;:!?)}\]'"])/gi;

interface LinkifyTextProps {
  text: string;
  className?: string;
  linkClassName?: string;
}

/** Render plain text with clickable http(s) links — safe for chat bubbles and reports. */
export function LinkifyText({ text, className, linkClassName }: LinkifyTextProps): JSX.Element {
  const parts = useMemo(() => {
    const segments: Array<{ type: "text" | "link"; value: string }> = [];
    let lastIndex = 0;
    for (const match of text.matchAll(URL_RE)) {
      const index = match.index ?? 0;
      if (index > lastIndex) {
        segments.push({ type: "text", value: text.slice(lastIndex, index) });
      }
      segments.push({ type: "link", value: match[0] });
      lastIndex = index + match[0].length;
    }
    if (lastIndex < text.length) {
      segments.push({ type: "text", value: text.slice(lastIndex) });
    }
    return segments.length ? segments : [{ type: "text" as const, value: text }];
  }, [text]);

  return (
    <span className={className}>
      {parts.map((part, index) =>
        part.type === "link" ? (
          <a
            key={`link-${index}`}
            href={part.value}
            target="_blank"
            rel="noopener noreferrer"
            className={cn("break-all text-cyan underline decoration-cyan/40 underline-offset-2 hover:text-pollen", linkClassName)}
          >
            {part.value}
          </a>
        ) : (
          <span key={`text-${index}`}>{part.value}</span>
        ),
      )}
    </span>
  );
}
