"use client";

interface SlackMarkdownPreviewProps {
  content: string;
  className?: string;
}

/** Render Slack-flavored markdown (*bold*, `code`, line breaks) for operator digests. */
export function SlackMarkdownPreview({ content, className }: SlackMarkdownPreviewProps): JSX.Element {
  try {
    const escaped = content
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
    const html = escaped
      .replace(/\*(.+?)\*/g, '<strong class="font-semibold text-(--qs-text)">$1</strong>')
      .replace(/`(.+?)`/g, '<code class="rounded bg-black/50 px-1 font-mono text-[0.9em] text-cyan">$1</code>')
      .replaceAll(/\n\n/g, "<br><br>")
      .replaceAll(/\n/g, "<br>");
    return (
      <div
        className={className ?? "text-xs leading-relaxed text-(--qs-text-2)"}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  } catch {
    return <pre className="whitespace-pre-wrap font-mono text-xs text-(--qs-text-2)">{content}</pre>;
  }
}
