import { redirect } from "next/navigation";

/** Legacy route — marketing site is promo-only; purchases happen on external marketplaces. */
export default function StartPage(): never {
  redirect("/skills");
}
