import { getLiveness } from "@/lib/api/health";

export async function BackendStatus() {
  let health = null;

  try {
    health = await getLiveness();
  } catch {
    health = null;
  }

  if (!health) {
    return (
      <section aria-labelledby="backend-status-title">
        <h2 id="backend-status-title">系统状态</h2>
        <p role="alert">暂时无法连接后端服务</p>
      </section>
    );
  } else
    return (
      <section aria-labelledby="backend-status-title">
        <h2 id="backend-status-title">系统状态</h2>
        <p>后端正常</p>
        <dl>
          <div>
            <dt>服务</dt>
            <dd>{health.service}</dd>
          </div>
          <div>
            <dt>版本</dt>
            <dd>{health.version}</dd>
          </div>
        </dl>
      </section>
    );
}
