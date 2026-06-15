/** Public marketing Eval-as-a-Service client (REV2). */

export interface MarketingEvalResult {
  passed: boolean;
  tier: string;
  score: number;
  issues: string[];
  critic_approved: boolean;
  skill_valid: boolean;
  eval_report_md: string;
  recommended_gumroad_price_eur_cents: number;
}

export async function runMarketingPublicEval(body: {
  title: string;
  workflow_markdown: string;
}): Promise<MarketingEvalResult> {
  const res = await fetch("/api/v1/marketing/eval", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `Eval unavailable (${res.status}).`;
    try {
      const payload = (await res.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await res.json()) as MarketingEvalResult;
}
