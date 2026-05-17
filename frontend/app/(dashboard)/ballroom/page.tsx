import Link from "next/link";

import { BallroomPanel } from "@/components/ballroom/ballroom-panel";
import { HivePageHeader } from "@/components/hive/hive-page-header";

export const dynamic = "force-dynamic";

export default function BallroomRoute() {
  return (
    <div className="space-y-6">
      <HivePageHeader
        title="Ballroom"
        subtitle="Realtime voice + chat lane integrated with supervisor sessions and live swarm orchestration."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/agents#sessions" className="qs-btn qs-btn--ghost qs-btn--sm">
              Supervisor sessions
            </Link>
            <Link href="/" className="qs-btn qs-btn--ghost qs-btn--sm">
              Dashboard
            </Link>
          </div>
        }
      />
      <section className="rounded-3xl border border-cyan/20 bg-[#070d17]/65 p-3 sm:p-4">
        <BallroomPanel showHeader={false} />
      </section>
    </div>
  );
}
