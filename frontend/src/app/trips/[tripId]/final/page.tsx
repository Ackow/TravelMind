import { Metadata } from "next";
import { FinalItinerary } from "@/components/trips/final/final-itinerary";

export const metadata: Metadata = {
  title: "最终行程 - TravelMind",
  description: "查看已确认的杭州至南京 5 日旅行计划完整日程、路线地图与出行提醒",
};

export default async function TripFinalPage({
  params,
}: {
  params: Promise<{ tripId: string }>;
}) {
  const { tripId } = await params;
  return <FinalItinerary tripId={tripId} />;
}
