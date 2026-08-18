import { Metadata } from "next";
import { VersionHistory } from "@/components/trips/history/version-history";

export const metadata: Metadata = {
  title: "计划版本历史 - TravelMind",
  description: "查看不可变旅行计划版本历史记录、变更对比与约束校验结果",
};

export default function HistoryPage() {
  return <VersionHistory tripId="tokyo-5d" />;
}
