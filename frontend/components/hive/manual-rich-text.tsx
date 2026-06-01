"use client";

import Link from "next/link";
import { Fragment, useMemo, type ReactNode } from "react";

const MARKDOWN_LINK_RE = /\[([^\]]+)\]\(([^)]+)\)/g;

interface ManualRichTextProps {
  text: string;
  className?: string;
}

/** Render manual copy with inline `[label](/path)` links. */
export function ManualRichText({ text, className }: ManualRichTextProps): ReactNode {
  const nodes = useMemo(() => {
    const parts: ReactNode[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;
    let key = 0;
    MARKDOWN_LINK_RE.lastIndex = 0;
    while ((match = MARKDOWN_LINK_RE.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index));
      }
      const label = match[1];
      const href = match[2];
      parts.push(
        <Link
          key={`manual-link-${key++}`}
          href={href}
          className="font-medium text-cyan underline decoration-cyan/40 underline-offset-2 hover:text-pollen hover:decoration-pollen/50"
        >
          {label}
        </Link>,
      );
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex));
    }
    if (parts.length === 0) {
      return [text];
    }
    return parts.map((part, index) => (
      <Fragment key={`manual-part-${index}`}>{part}</Fragment>
    ));
  }, [text]);

  return <span className={className}>{nodes}</span>;
}

interface ManualOpenLinkProps {
  href: string;
  label?: string;
}

/** Trailing CTA beside checklist steps. */
export function ManualOpenLink({ href, label = "Open" }: ManualOpenLinkProps): ReactNode {
  return (
    <Link
      href={href}
      className="ml-2 inline-flex shrink-0 items-center gap-0.5 rounded-md border border-cyan/30 bg-cyan/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-cyan hover:border-pollen/40 hover:bg-pollen/10 hover:text-pollen"
    >
      {label}
      <span aria-hidden>→</span>
    </Link>
  );
}
