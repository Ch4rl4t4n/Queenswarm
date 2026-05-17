import { redirect } from "next/navigation";

/**
 * Backward-compatible alias for historical hierarchy deep-links under /agents.
 */
export default function AgentsHierarchyAliasPage(): never {
  redirect("/agents#hierarchy");
}
