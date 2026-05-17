import { redirect } from "next/navigation";

/**
 * Backward-compatible alias for historical supervisor sessions route variants.
 */
export default function AgentsSessionsAliasPage(): never {
  redirect("/agents#sessions");
}
