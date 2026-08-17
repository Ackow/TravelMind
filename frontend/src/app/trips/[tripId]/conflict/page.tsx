import { ConflictResolution } from "@/components/trips/unfeasible/conflict-resolution";

export const metadata = {
  title: "当前条件下无法生成可行计划 - TravelMind",
  description: "硬性约束冲突解析与安全调整",
};

export default async function TripConflictPage({
  params,
}: {
  params: Promise<{ tripId: string }>;
}) {
  const { tripId } = await params;
  return <ConflictResolution tripId={tripId} />;
}
