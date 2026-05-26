import type { Metadata } from "next";

import { FactoryPageClient } from "@/components/hive/factory-page-client";

export const metadata: Metadata = {
  title: "Factory · Queenswarm",
  description: "Micro-SaaS Factory — simulate-first MVP blueprint for solo operators.",
};

export default function DashboardFactoryPage(): JSX.Element {
  return <FactoryPageClient />;
}
