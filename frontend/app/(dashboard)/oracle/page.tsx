import { redirect } from "next/navigation";

/** Legacy route — Oracle removed; priorities live on Agentic OS overview. */
export default function OraclePage() {
  redirect("/agentic-os");
}
