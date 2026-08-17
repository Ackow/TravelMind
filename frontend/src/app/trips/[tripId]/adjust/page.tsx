import { ItineraryEditor } from "@/components/trips/itinerary-editor";

export default async function AdjustTripPage({
  params,
}: {
  params: Promise<{ tripId: string }>;
}) {
  const { tripId } = await params;
  return <ItineraryEditor tripId={tripId} />;
}
