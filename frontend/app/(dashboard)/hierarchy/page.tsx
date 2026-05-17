import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

/**
 * Org-chart route removed from primary IA; bookmarks redirect to the live roster anchor.
 */
export default function HierarchyRedirectPage(): never {
  /* Hash is dropped from HTTP redirects; hierarchy is rendered on `/agents`. */
  redirect("/agents");
}
