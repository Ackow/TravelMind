import { Metadata } from "next";
import { HistoryPlansList } from "@/components/trips/history-plans-list";

export const metadata: Metadata = {
  title: "历史旅行计划 - TravelMind",
  description: "查看与管理所有生成的行程计划、版本演进对比与详细路书",
};

export default function HistoryPage() {
  return <HistoryPlansList />;
}
