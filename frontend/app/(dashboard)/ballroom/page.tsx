import { BallroomPanel } from "@/components/ballroom/ballroom-panel";

export const dynamic = "force-dynamic";

export default function BallroomRoute() {
  return (
    <div className="px-1 sm:px-0">
      <BallroomPanel />
    </div>
  );
}
