import type { MaybeLocalizedString, MaybeLocalizedStringList } from "@/lib/ui-language";

/** Phase C social publish — operator setup steps for InfoHint on marketplace cards. */

export const SOCIAL_PUBLISH_TEMPLATE_IDS = new Set([
  "instagram_graph_api",
  "facebook_graph_api",
  "twitter_api_v2",
  "tiktok_content_posting",
]);

const SHARED_STEPS: { en: string[]; sk: string[] } = {
  en: [
    "Tools Marketplace → install this connector (Social publish pack).",
    "Meta: OAUTH_META_* · X: OAUTH_X_* · TikTok: OAUTH_TIKTOK_* in .env.prod.oauth → redeploy → Hub → Connect.",
    "Marketing Ops swarm → outputs a publish pack with channel + media_url (image or video).",
    "Publish Queue → operator approves the pack.",
    "Execution Studio → Social publish → Simulate to verify caption and media preview.",
    "When OAuth works → set SOCIAL_PUBLISH_LIVE_ENABLED=true in .env.prod → redeploy → Live.",
    "Full guide: docs/OPERATOR_SOCIAL_OAUTH_SETUP.md (Meta, X, TikTok, newsletter).",
  ],
  sk: [
    "Tools Marketplace → nainštaluj tento connector (balík Social publish).",
    "Meta: OAUTH_META_* · X: OAUTH_X_* · TikTok: OAUTH_TIKTOK_* v .env.prod.oauth → redeploy → Hub → Connect.",
    "Marketing Ops swarm → vygeneruje publish pack s channel + media_url (obrázok alebo video).",
    "Publish Queue → operátor schváli pack.",
    "Execution Studio → Social publish → Simulate (over preview).",
    "Keď OAuth funguje → v .env.prod nastav SOCIAL_PUBLISH_LIVE_ENABLED=true → redeploy → Live.",
    "Podrobný návod: docs/OPERATOR_SOCIAL_OAUTH_SETUP.md (Meta, X, TikTok, newsletter).",
  ],
};

const CHANNEL_NOTES: Record<
  string,
  { title: { en: string; sk: string }; description: { en: string; sk: string } }
> = {
  instagram_graph_api: {
    title: { en: "Instagram setup", sk: "Nastavenie Instagram" },
    description: {
      en: "Meta Business or Creator account required. After OAuth, pass ig_user_id when publishing (photo/video + caption).",
      sk: "Vyžaduje Meta Business alebo Creator účet. Po OAuth zadaj ig_user_id pri publikovaní (foto/video + popis).",
    },
  },
  facebook_graph_api: {
    title: { en: "Facebook setup", sk: "Nastavenie Facebook" },
    description: {
      en: "Connect a Facebook Page via Meta OAuth. Use page_id for feed or photo posts from approved publish packs.",
      sk: "Pripoj Facebook Page cez Meta OAuth. Pri postoch použij page_id — text alebo foto z publish packu.",
    },
  },
  twitter_api_v2: {
    title: { en: "X (Twitter) setup", sk: "Nastavenie X (Twitter)" },
    description: {
      en: "X Developer app with OAuth2 user context. Caption is truncated to 280 characters automatically.",
      sk: "X Developer app s OAuth2 user kontextom. Popis sa automaticky skráti na 280 znakov.",
    },
  },
  tiktok_content_posting: {
    title: { en: "TikTok setup", sk: "Nastavenie TikTok" },
    description: {
      en: "TikTok Content Posting API — publish pack must include a video media_url. Poll status after init.",
      sk: "TikTok Content Posting API — publish pack musí obsahovať video media_url. Po init skontroluj status.",
    },
  },
};

export function socialConnectorOperatorHint(templateId: string | undefined): {
  title: MaybeLocalizedString;
  description: MaybeLocalizedString;
  options: MaybeLocalizedStringList;
} | null {
  if (!templateId || !SOCIAL_PUBLISH_TEMPLATE_IDS.has(templateId)) {
    return null;
  }
  const notes = CHANNEL_NOTES[templateId];
  if (!notes) {
    return null;
  }
  return {
    title: notes.title,
    description: notes.description,
    options: SHARED_STEPS,
  };
}

export const SOCIAL_PUBLISH_PANEL_HINT = {
  title: {
    en: "Social publish — operator guide",
    sk: "Social publish — návod pre operátora",
  },
  description: {
    en: "Post approved publish packs (graphics + captions) to Instagram, Facebook, X, TikTok, and Gmail newsletter. Default is simulate-only until live is enabled.",
    sk: "Publikuj schválené publish packy na Instagram, Facebook, X, TikTok a Gmail newsletter. Predvolene len simulate, kým nezapneš live.",
  },
  options: SHARED_STEPS,
};
