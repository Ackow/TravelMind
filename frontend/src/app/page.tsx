import { BackendStatus } from "@/components/system/backend-status";


export default function HomePage() {
  return (
    <main>
      <header>
        <p>TravelMind</p>
        <h1>动态旅行规划 Agent</h1>
        <p>根据实时信息、约束和用户反馈持续调整旅行计划。</p>
      </header>

      <BackendStatus />
    </main>
  )
}