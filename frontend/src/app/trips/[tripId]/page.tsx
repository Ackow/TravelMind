import { TripDetail } from "@/components/trips/trip-detail";

export default async function TripPage({
  params,
}: {
  params: Promise<{ tripId: string }>;
}) {
  const { tripId } = await params;
  return (
    <main>
      <TripDetail tripId={tripId} />
    </main>
  );
}
