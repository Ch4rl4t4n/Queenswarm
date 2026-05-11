import { BallroomPanel } from "@/components/ballroom/ballroom-panel";

export const dynamic = "force-dynamic";

export default function BallroomRoute() {
  return (
    <div className="space-y-10">
      <div>
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase tracking-[0.32em] text-cyan">
          phase j · ballroom bridge
        </p>
      </div>
      <BallroomPanel />
    </div>
  );
}
