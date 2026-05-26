/** Operator-facing copy for Grok live voice failures (no raw xAI JSON dumps). */

export function formatVoiceLiveError(raw: string): string {
  const text = raw.trim();
  const lowered = text.toLowerCase();

  if (!text) {
    return "Voice chat sa nepodarilo spustiť.";
  }
  if (lowered.includes("not configured")) {
    return "Grok API kľúč chýba — pridaj ho v Settings → LLM keys.";
  }
  if (lowered.includes("incorrect api key") || lowered.includes("neplatný")) {
    return "Grok API kľúč je neplatný — vytvor nový na console.x.ai a ulož ho v Settings → LLM keys.";
  }
  if (lowered.includes("sign_in") || lowered.includes("session")) {
    return "Session vypršala — prihlás sa znova.";
  }
  if (lowered.includes("rate limit")) {
    return "Rate limit — počkaj pár sekúnd a skús znova.";
  }
  if (text.startsWith("xAI voice token failed:")) {
    return "Grok voice nedostupný — skontroluj API kľúč v Settings → LLM keys.";
  }
  return text.length > 160 ? `${text.slice(0, 157)}…` : text;
}
