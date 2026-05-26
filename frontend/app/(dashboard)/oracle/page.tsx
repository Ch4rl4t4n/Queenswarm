"use client";

import { LazyHiveOraclePanel } from "@/components/hive/hive-oracle-panel";

export default function OraclePage() {
  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4 lg:p-6">
      <LazyHiveOraclePanel />
    </div>
  );
}
