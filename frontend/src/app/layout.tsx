import "@daypicker/react/style.css";

import { SiteHeader } from "@/components/system/site-header";

import "./globals.css";

export const metadata = {
  title: "TravelMind",
  description: "清晰、可靠、可调整的旅行规划工作台",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="zh-CN">
      <body>
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
