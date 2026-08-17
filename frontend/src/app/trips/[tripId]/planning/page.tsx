import { PlanningProgress } from "@/components/trips/planning-progress";

export default async function PlanningPage({
  params,
}: {
  params: Promise<{ tripId: string }>;
}) {
  const { tripId } = await params;
  return <PlanningProgress tripId={tripId} />;
}
