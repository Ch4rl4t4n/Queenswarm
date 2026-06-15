"use client";

import Link from "next/link";
import { useState } from "react";

import { LacIcon } from "@/components/marketing/lac-icons";
import {
  HARNESS_EVAL_DEFAULT_MARKDOWN,
  HARNESS_EVAL_DEFAULT_TITLE,
} from "@/lib/harness-eval-default-workflow";
import { runMarketingPublicEval, type MarketingEvalResult } from "@/lib/marketing-eval";

function downloadReport(title: string, markdown: string): void {
  const slug = title.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-") || "eval-report";
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${slug}-EVAL_REPORT.md`;
  anchor.click();
  URL.revokeObjectURL(url);
}

/** REV2 — public Eval-as-a-Service lead magnet page. */
export function MarketingEvalPageClient(): JSX.Element {
  const [title, setTitle] = useState(HARNESS_EVAL_DEFAULT_TITLE);
  const [markdown, setMarkdown] = useState(HARNESS_EVAL_DEFAULT_MARKDOWN);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MarketingEvalResult | null>(null);

  const runEval = async (): Promise<void> => {
    if (markdown.trim().length < 40) {
      setError("Workflow must be at least 40 characters.");
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const data = await runMarketingPublicEval({
        title: title.trim() || "Submitted workflow",
        workflow_markdown: markdown,
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Eval failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mk-wrap">
      <div className="mk-static-hero">
        <span className="mk-eyebrow">
          <LacIcon name="flask" size={13} />
          Free eval
        </span>
        <h1 style={{ marginTop: 16 }}>Check your agent workflow before you sell it.</h1>
        <p>
          Paste SKILL.md or workflow markdown — get a simulate-first EVAL_REPORT with PASS/FAIL, tier, and Gumroad
          price hint. Heuristic check only; no account required.
        </p>
      </div>

      <section className="mk-section" style={{ paddingTop: 24 }}>
        <div className="glass" style={{ padding: 28 }}>
          <label className="block text-sm" style={{ marginBottom: 16 }}>
            <span className="text-2">Title</span>
            <input
              type="text"
              className="mk-input mt-2 w-full"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={200}
            />
          </label>

          <label className="block text-sm">
            <span className="text-2">Workflow / SKILL.md</span>
            <textarea
              className="mk-input mt-2 min-h-[220px] w-full font-mono text-xs"
              value={markdown}
              onChange={(e) => setMarkdown(e.target.value)}
            />
          </label>

          <div className="row gap-3 mt-4" style={{ flexWrap: "wrap" }}>
            <button type="button" className="btn btn-gold" disabled={busy} onClick={() => void runEval()}>
              {busy ? "Running eval…" : "Run free eval"}
            </button>
            <Link href="/skills" className="btn btn-primary">
              Browse verified catalog
            </Link>
          </div>

          {error ? (
            <p className="text-4 mt-4" style={{ color: "var(--magenta)" }}>
              {error}
            </p>
          ) : null}

          {result ? (
            <div className="mk-trust-card mt-6" style={{ padding: 22 }}>
              <div className="row gap-3" style={{ alignItems: "center", flexWrap: "wrap" }}>
                <span className={`mk-type skill${result.passed ? "" : ""}`}>
                  <LacIcon name={result.passed ? "shield" : "flask"} size={12} />
                  {result.passed ? "PASS" : "FAIL"}
                </span>
                <span className="text-3 fs-13">
                  tier {result.tier} · score {Math.round(result.score * 100)}%
                </span>
                <span className="gold fs-13 font-mono">
                  Gumroad hint €{(result.recommended_gumroad_price_eur_cents / 100).toFixed(2)}
                </span>
              </div>
              {result.issues.length > 0 ? (
                <ul className="mk-checklist mt-4" style={{ fontSize: 13 }}>
                  {result.issues.slice(0, 8).map((issue) => (
                    <li key={issue}>
                      <LacIcon name="spark" size={16} />
                      <span>{issue}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
              <button
                type="button"
                className="btn btn-primary mt-4"
                onClick={() => downloadReport(title, result.eval_report_md)}
              >
                Download EVAL_REPORT.md
              </button>
            </div>
          ) : null}
        </div>

        <p className="text-3 fs-12 mt-6" style={{ lineHeight: 1.6, maxWidth: 640 }}>
          Need full LLM critic + factory packaging? Operators use Queenswarm Skill Factory. Buyers get simulate-first
          verified listings on{" "}
          <Link href="/skills" className="gold">
            the catalog
          </Link>
          .
        </p>
      </section>
    </div>
  );
}
