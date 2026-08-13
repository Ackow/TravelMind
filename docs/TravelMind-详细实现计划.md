# TravelMind 详细实现计划

> 目标读者：希望亲手逐步实现项目，并理解 Agent、工具调用、状态、约束规划、反馈循环和评估每一个环节的开发者。
>
> 本文依据仓库根目录的《项目说明.md》制定。当前仓库尚无业务代码，因此采用从零构建、逐阶段形成可运行闭环的路线。

## 1. 最终要做成什么

TravelMind 不是“用户提问，LLM 一次生成攻略”的聊天应用，而是一个拥有显式状态和反馈循环的动态旅行规划 Agent：

```text
用户输入
  → 结构化约束
  → 调用天气 / POI / 路线工具
  → 生成候选行程
  → 程序化约束检查
  → 不通过则修正
  → 用户审阅
  → 合并新反馈并局部重规划
  → 最终行程
```

完成 MVP 后，系统应能演示以下主流程：

1. 创建一个单城市、3～7 天的旅行。
2. 查询或模拟天气、景点、地点间交通时间。
3. 生成带时间、交通、费用的逐日行程。
4. 自动发现闭馆、预算超限、时间冲突、路线不合理等问题。
5. 根据规则和 Agent 循环修正方案。
6. 接收“少走路”“删除某景点”“明天下雨”等自然语言反馈。
7. 保留未受影响的安排，只重规划必要部分。
8. 展示规划过程、工具调用与约束检查结果。
9. 保存版本历史，并导出最终 Markdown；PDF 作为增强项。

## 2. 范围边界

### 2.1 MVP 必做

- 单个目的地城市。
- 3～7 天行程。
- 1～6 位出行者。
- 天气、POI、路线、预算四类数据。
- 结构化旅行状态。
- 硬约束与软偏好分离。
- 初次规划和用户反馈后的重规划。
- 计划版本、变更说明和基础 Agent Trace。
- 真实 API 可替换的 Mock 工具。
- 核心规则、API 和 Agent 流程的自动化测试。

### 2.2 MVP 明确不做

- 机票、酒店、门票的真实下单和支付。
- 多城市、多国家联程规划。
- 复杂账号体系和社交功能。
- 实时导航或 GPS 轨迹。
- 自研全局最优路径算法。
- 一开始就拆微服务、上 Redis、Kubernetes 或消息队列。

这些能力会显著增加工程量，却不会帮助你先理解 Agent 的核心闭环。

## 3. 建议技术方案

### 3.1 技术栈

| 层 | 选择 | 主要职责 |
|---|---|---|
| 前端 | Next.js、React、TypeScript、Tailwind CSS | 创建旅行、显示规划进度、编辑和审阅行程 |
| 后端 | Python、FastAPI、Pydantic | API、领域逻辑、工具适配、Agent 调度 |
| Agent | LangGraph + 一个支持结构化输出/Tool Calling 的模型 | 工作流、条件分支、暂停与恢复、重规划 |
| 数据库 | PostgreSQL；开发初期可先 SQLite | 旅行状态、计划版本、反馈、工具调用记录 |
| 外部数据 | 天气、地点、路线 API | 提供可验证的事实，而非让模型编造 |
| 协议 | MCP，后置实现 | 将旅行工具以标准协议暴露给 Agent |
| 测试 | pytest、FastAPI TestClient、前端测试工具、Playwright | 单元、集成和端到端验证 |

不要在本文中写死依赖版本。每进入一个阶段时选稳定版本、锁入依赖文件，并记录升级理由。

### 3.2 总体架构

```text
┌──────────────── Next.js Web ────────────────┐
│ 创建表单 │ 规划进度 │ 行程时间轴 │ 反馈输入 │
└───────────────────┬─────────────────────────┘
                    │ HTTP + SSE
┌───────────────────▼─────────────────────────┐
│                 FastAPI                      │
│ API 路由 │ 应用服务 │ DTO 校验 │ 错误处理     │
├───────────────────┬─────────────────────────┤
│              Travel Agent / LangGraph        │
│ 解析 → 研究 → 规划 → 规则检查 → 修正 → 审阅  │
├──────────────┬────┴─────────┬───────────────┤
│ Weather Tool │ POI Tool     │ Route Tool    │
│ Mock / API   │ Mock / API   │ Mock / API    │
├──────────────┴──────────────┴───────────────┤
│ 领域模型 │ 约束引擎 │ 预算计算 │ 版本差异       │
├─────────────────────────────────────────────┤
│ PostgreSQL │ Checkpoint │ Trace / Evaluation │
└─────────────────────────────────────────────┘
```

核心依赖方向必须保持为：

```text
API / Agent / Infrastructure → Application → Domain
```

`domain` 不应导入 FastAPI、LangGraph、数据库 ORM 或具体第三方 API。这样规则引擎可以脱离模型和网络独立测试。

## 4. 推荐目录结构

```text
TravelMind/
├─ README.md
├─ .env.example
├─ docker-compose.yml
├─ docs/
│  ├─ TravelMind-详细实现计划.md
│  ├─ architecture.md
│  ├─ api-contract.md
│  └─ decisions/
├─ backend/
│  ├─ pyproject.toml
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/
│  │  │  ├─ dependencies.py
│  │  │  └─ routes/
│  │  ├─ core/
│  │  │  ├─ config.py
│  │  │  ├─ errors.py
│  │  │  └─ logging.py
│  │  ├─ domain/
│  │  │  ├─ models.py
│  │  │  ├─ constraints.py
│  │  │  ├─ budget.py
│  │  │  └─ replanning.py
│  │  ├─ application/
│  │  │  ├─ trip_service.py
│  │  │  └─ planning_service.py
│  │  ├─ agent/
│  │  │  ├─ state.py
│  │  │  ├─ graph.py
│  │  │  ├─ nodes.py
│  │  │  └─ prompts/
│  │  ├─ tools/
│  │  │  ├─ protocols.py
│  │  │  ├─ mock/
│  │  │  └─ providers/
│  │  ├─ persistence/
│  │  │  ├─ models.py
│  │  │  ├─ repositories.py
│  │  │  └─ migrations/
│  │  └─ schemas/
│  └─ tests/
│     ├─ unit/
│     ├─ integration/
│     ├─ contract/
│     └─ fixtures/
├─ frontend/
│  ├─ package.json
│  ├─ src/
│  │  ├─ app/
│  │  ├─ components/
│  │  ├─ features/trips/
│  │  ├─ lib/api/
│  │  └─ types/
│  └─ tests/
└─ mcp-server/                 # MVP 主闭环完成后再添加
```

目录可以逐阶段创建，不要第一天生成大量空文件。

## 5. 先统一领域语言

### 5.1 核心对象

建议首先定义以下对象，而不是直接写 Prompt：

- `TripRequest`：用户最初提交的旅行需求。
- `TripPreferences`：兴趣、饮食、住宿、交通等软偏好。
- `TripConstraints`：预算、日期、每日结束时间、最大步行量等约束。
- `WeatherSnapshot`：某城市某天的天气事实和数据来源时间。
- `Place`：地点事实，包括坐标、分类、营业时间、费用、建议时长。
- `RouteLeg`：两个地点间某种交通方式的距离、耗时、步行量和费用。
- `Activity`：行程中的一个活动，包含开始/结束时间及关联地点。
- `DayPlan`：某一天的一组活动和每日统计。
- `Itinerary`：完整计划和总预算。
- `ConstraintViolation`：机器可理解的约束违反结果。
- `PlanVersion`：每次规划或重规划产生的不可变快照。
- `UserFeedback`：原始反馈、解析后的变更指令和作用范围。
- `PlanningEvent`：供前端显示的安全 Trace 事件。

### 5.2 硬约束与软偏好

硬约束不满足时计划不能通过，例如：

- 活动发生在景点关闭时间之后。
- 两个活动之间没有足够交通时间。
- 日期超出旅行范围。
- 总费用超过硬预算。
- 每日结束时间晚于用户规定上限。

软偏好用于评分和取舍，例如：

- 更喜欢动漫或美食。
- 倾向公共交通。
- 尽量少走路。
- 希望行程轻松。

每条规则返回结构化结果：

```json
{
  "code": "PLACE_CLOSED",
  "severity": "error",
  "day": "2026-10-02",
  "activity_id": "act_123",
  "message": "计划到达时间晚于闭馆时间",
  "actual": "17:30",
  "expected": "before 17:00",
  "repair_hint": "提前该活动或替换地点"
}
```

`code` 用于程序分支，`message` 用于展示，不能只返回自然语言。

## 6. 分阶段实现路线

每个阶段都遵循同一节奏：先写最小设计说明，再写测试，再实现，再手动演示，最后提交一个可回退的 Git commit。

### 阶段 0：建立工程基线

**学习目标**：理解前后端如何独立运行、配置和通信。

**实施步骤**：

1. 创建根目录 `README.md`，写明产品范围、启动方式和当前阶段。
2. 创建 `backend` Python 项目，添加 FastAPI、Pydantic、测试与格式化配置。
3. 创建 `frontend` Next.js TypeScript 项目。
4. 添加 `.gitignore`，排除 `.venv`、依赖、构建产物、环境变量和 IDE 状态。
5. 添加 `.env.example`，只放变量名和说明，不放密钥。
6. 后端实现 `GET /health`，前端首页显示后端健康状态。
7. 配置统一命令：后端启动、前端启动、后端测试、前端检查。

**验收**：

- 新环境按 README 能启动两个进程。
- 浏览器能看到 API 健康状态。
- 测试与静态检查命令均成功。
- 仓库中不存在真实 API Key。

**建议提交**：`chore: bootstrap frontend and backend`

### 阶段 1：领域模型与固定样例数据

**学习目标**：理解结构化状态为什么是 Agent 可控性的基础。

**实施步骤**：

1. 用 Pydantic 定义第 5 节核心对象。
2. 所有金额使用明确币种；内部金额建议使用最小货币单位整数或 Decimal。
3. 所有日期时间都带目的地时区；不要用无时区 `datetime`。
4. 为东京 5 日游编写固定 JSON fixture：天气、10～20 个 POI、路线矩阵。
5. 编写 fixture 加载器和数据校验测试。
6. 写一个纯 Python 脚本，将固定输入转换为空白 `Itinerary` 骨架并输出 JSON。

**需要亲手回答**：

- 用户输入、领域状态、数据库记录为什么不能共用一个大模型？
- 缺失值与未知值有什么区别？
- 为什么工具数据要记录 `source`、`fetched_at` 和 `expires_at`？

**验收**：非法日期、负预算、结束日期早于开始日期、无坐标 POI 均能被明确拒绝。

**建议提交**：`feat: define trip domain models and fixtures`

### 阶段 2：实现不依赖 LLM 的约束引擎

**学习目标**：区分确定性计算与概率性推理。

**实施步骤**：

1. 定义统一 `ConstraintRule` 接口：输入行程和上下文，输出违反列表。
2. 逐条实现并测试：
   - 日期范围规则；
   - 营业时间规则；
   - 活动时间重叠规则；
   - 交通衔接规则；
   - 每日最晚结束规则；
   - 每日最大步行量规则；
   - 天气与室内/户外兼容规则；
   - 每日及总预算规则。
3. 实现 `ConstraintEngine.check()` 汇总结果。
4. 区分 `error`、`warning` 和 `info`。
5. 对边界值写参数化测试，例如刚好闭馆、刚好用完预算。

**重要原则**：规则只判断事实，不直接让 LLM 决定“是否超预算”或“是否赶得上”。

**验收**：为每类规则至少准备一个通过用例和两个失败/边界用例；同一输入的结果完全确定。

**建议提交**：`feat: add deterministic constraint engine`

### 阶段 3：用算法生成第一版可行计划

**学习目标**：先理解规划问题，再让 LLM参与高层决策。

**实施步骤**：

1. 按用户偏好、评分、费用和室内/户外匹配给 POI 打分。
2. 按坐标或路线耗时把 POI 粗略分区。
3. 每天选定一个区域，减少跨城折返。
4. 在营业时间和每日时间窗内贪心插入活动。
5. 插入 `RouteLeg` 和用餐/休息缓冲时间。
6. 调用约束引擎；若失败，按明确策略删除、提前或替换低优先级活动。
7. 限制修正轮数，超过上限返回“无法满足”及原因，禁止死循环。

此阶段允许算法不聪明，但必须可解释、可复现、可测试。

**验收场景**：

- 晴天生成室内外混合行程。
- 雨天减少户外活动。
- 低预算时选择免费/低价地点。
- 最大步行量较低时减少地点数量或更换交通方式。
- 无解时明确指出冲突约束，而不是伪造可行计划。

**建议提交**：`feat: build deterministic itinerary planner`

### 阶段 4：设计 REST API

**学习目标**：理解应用层用例、API DTO 和领域对象的边界。

**首批接口**：

```text
POST   /api/v1/trips                    创建旅行
GET    /api/v1/trips/{trip_id}          获取旅行状态
POST   /api/v1/trips/{trip_id}/plan     启动初次规划
GET    /api/v1/trips/{trip_id}/plans    获取版本列表
GET    /api/v1/trips/{trip_id}/plans/{version}
POST   /api/v1/trips/{trip_id}/feedback 提交反馈并重规划
GET    /api/v1/trips/{trip_id}/events   获取规划事件（后续升级 SSE）
GET    /health
```

**实施步骤**：

1. 先在 `docs/api-contract.md` 写请求、响应和错误样例。
2. 路由只做输入校验、调用应用服务和映射响应。
3. 为不存在、校验失败、外部工具失败、规划无解设计稳定错误码。
4. 使用内存 Repository 完成第一版，不急着接数据库。
5. 写 API 集成测试，覆盖成功和主要失败分支。

**验收**：只用 API 客户端即可完成“创建 → 规划 → 查看计划 → 提反馈 → 查看新版本”。

**建议提交**：`feat: expose trip planning API`

### 阶段 5：实现最小前端闭环

**学习目标**：理解服务器状态、表单状态和 Agent 运行状态的区别。

**页面顺序**：

1. 创建旅行页：分组表单、前端基础校验、明确币种和时区。
2. 规划进度页：显示当前阶段和公开 Trace，不展示模型私有推理。
3. 草案页：先做日切换 + 时间轴 + 预算/天气摘要；地图先用占位区。
4. 修改区：提交自然语言反馈，展示变更前后摘要。
5. 最终行程页：适合打印的布局和 Markdown 导出。

**状态要求**：

- `idle`：尚未规划。
- `researching`：查询外部数据。
- `planning`：生成候选方案。
- `validating`：规则检查。
- `needs_review`：等待用户确认。
- `replanning`：根据反馈更新。
- `completed`：用户接受。
- `failed`：可恢复错误。

**验收**：刷新页面不会丢失当前 trip id；加载、空状态、错误状态和重试入口完整。

**建议提交**：`feat: add end-to-end trip planning UI`

### 阶段 6：接入 LLM，但限制其职责

**学习目标**：掌握结构化输出、Prompt 边界、失败降级和模型不可确定性。

LLM 适合负责：

- 将自然语言补充要求解析为结构化变更。
- 在多个可行候选间做偏好排序。
- 生成行程说明、选择理由和变更摘要。
- 根据约束违反结果提出修正动作。

LLM 不负责：

- 计算距离、金额和时间差。
- 判断景点是否真实存在或是否营业。
- 保存权威状态。
- 绕过约束引擎宣告计划可行。

**实施步骤**：

1. 抽象 `LLMClient` 接口，业务代码不依赖具体供应商 SDK。
2. 第一个模型任务只做“反馈 → 结构化 Patch”。
3. 使用严格 Schema 校验输出；失败时有限重试，仍失败则要求用户澄清。
4. 第二个模型任务做“候选排序”，输入只能包含工具返回的 POI。
5. 第三个模型任务做“修正动作建议”，随后仍由程序执行并复检。
6. 保存 prompt 版本、模型名、耗时、token 用量和结果状态。
7. 测试中使用 Fake LLM，避免单元测试依赖网络和费用。

结构化反馈示例：

```json
{
  "operations": [
    {"op": "remove_place", "place_name": "银座"},
    {"op": "add_preference", "value": "动漫", "weight": 0.9}
  ],
  "scope": {"days": [3]},
  "requires_clarification": false
}
```

**验收**：模型输出格式错误不会污染 TripState；模型建议违反硬约束时会被拒绝并进入修正流程。

**建议提交**：`feat: add structured llm planning assistance`

### 阶段 7：工具抽象与真实数据接入

**学习目标**：掌握第三方 API 隔离、契约转换、缓存、限流和降级。

**统一工具接口**：

```text
WeatherTool.get_forecast(city, date_range)
PoiTool.search(city, categories, preferences)
PoiTool.get_detail(place_id)
RouteTool.get_matrix(origins, destinations, mode)
RouteTool.get_route(origin, destination, mode)
```

**实施顺序**：

1. 先让 Mock 实现通过契约测试。
2. 接入一个天气 Provider，并将第三方响应映射为内部模型。
3. 接入 POI Provider；验证坐标、类别、营业时间和来源。
4. 接入路线 Provider；优先使用矩阵接口减少调用次数。
5. 用同一组契约测试验证 Mock 和真实 Adapter 的返回语义一致。
6. 添加超时、有限重试、并发上限、缓存和错误映射。
7. 数据缺失时保留 `unknown`，不要由 LLM 补造。

**降级策略**：

| 故障 | MVP 行为 |
|---|---|
| 天气不可用 | 标记未知，提示计划未做天气优化 |
| POI 搜索不可用 | 使用有时效提示的缓存/样例数据 |
| 单个 POI 详情失败 | 排除该地点或标记需人工确认 |
| 路线不可用 | 使用直线距离保守估算，并标记估算值 |
| API 限流 | 退避后重试一次，随后返回可恢复错误 |

**验收**：切换环境变量即可在 Mock 与真实 Provider 间切换；第三方字段不会泄漏到领域层。

**建议提交**：`feat: integrate travel data providers`

### 阶段 8：用 LangGraph 编排 Agent 循环

**学习目标**：理解节点、边、共享状态、条件路由、暂停/恢复和循环上限。

**建议节点**：

```text
parse_request
  → validate_request
  → research_weather
  → research_pois
  → research_routes
  → build_candidate
  → check_constraints
       ├─ pass → prepare_review → interrupt
       └─ fail → propose_repairs → apply_repairs
                                  → check_constraints
user_feedback
  → parse_feedback
  → apply_feedback_patch
  → determine_impact
  → refresh_stale_data
  → replan_affected_scope
  → check_constraints
```

**State 至少包含**：

- `trip_id`、`request`、`preferences`、`constraints`。
- 工具返回的事实及新鲜度。
- 候选地点和当前行程。
- 约束违反列表和修正次数。
- 用户反馈历史。
- 当前计划版本与受影响范围。
- `status`、`last_error` 和公开事件。

**实施步骤**：

1. 先把阶段 3～7 已测试的函数包成节点，不在节点内重写业务逻辑。
2. 每个节点只承担一个清晰职责。
3. 每个节点声明读取和写入哪些 State 字段。
4. 为修正循环添加最大次数和无进展检测。
5. 在用户审阅处设置 interrupt/checkpoint。
6. 模拟进程重启后从 checkpoint 恢复。
7. 为节点路由和完整图写集成测试。

**验收**：Trace 能证明工具、状态、约束、反馈和执行确实形成闭环；不是在一个节点里用超长 Prompt 假装 Agent。

**建议提交**：`feat: orchestrate planning with langgraph`

### 阶段 9：真正的动态重规划

**学习目标**：理解状态 Patch、影响分析、局部重算和版本差异。

**反馈处理链**：

```text
原始文本
→ 结构化 operations
→ 合法性检查
→ 更新约束/偏好
→ 计算影响范围
→ 锁定不受影响部分
→ 重规划受影响天/活动
→ 全局复检
→ 生成新版本和 diff
```

**先支持的操作**：

- 添加/删除偏好。
- 删除/替换/固定某个地点。
- 修改预算、步行量、每日结束时间。
- 指定某天晚出发。
- 将某活动固定在某天或时段。
- 天气变化触发的室内替换。

**重要数据**：每个 Activity 增加 `locked`、`priority`、`source` 和稳定 ID。局部重规划时，未受影响活动保持 ID 和时间，便于生成可靠 diff。

**验收场景**：

1. “移除银座”只影响包含银座的那一天。
2. “每天少走路”可能影响所有天，并在 diff 中说明原因。
3. “今天 11:30 才能出发”保留今日高优先级项目，未来天不变。
4. “明天下雨”优先交换已有天次，其次再搜索室内替代。
5. 用户要求互相冲突时进入澄清/无解状态，不擅自忽略某一项。

**建议提交**：`feat: support scoped dynamic replanning`

### 阶段 10：持久化、版本与恢复

**学习目标**：理解业务状态、Agent checkpoint 和审计日志的差别。

**建议表**：

```text
trips
trip_preferences
trip_constraints
plan_versions
user_feedback
planning_runs
planning_events
tool_calls
```

`plan_versions` 保存不可变 JSON 快照和父版本号；`trips` 指向当前版本。不要覆盖旧版本。

**实施步骤**：

1. 将内存 Repository 换为数据库实现。
2. 添加迁移工具和首个 migration。
3. 保证创建版本与更新当前版本指针处于同一事务。
4. 为一次规划生成 `run_id`，关联所有事件和工具调用。
5. 配置 LangGraph checkpoint 持久化。
6. 测试重启恢复、重复请求和并发更新冲突。

**验收**：后端重启后仍能恢复旅行、版本、反馈和暂停中的规划；重复提交不会无意生成多份相同计划。

**建议提交**：`feat: persist trips plans and checkpoints`

### 阶段 11：将工具迁移为 MCP Server

**学习目标**：理解 MCP 的价值是工具发现和协议解耦，而不是给普通函数换名字。

**实施步骤**：

1. 先保持现有 Tool Protocol 不变，新增 MCP Client Adapter。
2. 创建独立 `travel-mcp-server`，暴露：
   - `get_weather`；
   - `search_poi`；
   - `get_place_detail`；
   - `get_route`；
   - 可选 `search_local_event`。
3. 为每个工具定义严格输入输出 Schema、超时和错误语义。
4. 将真实 Provider 调用移动或复用到 MCP Server。
5. 后端可通过配置切换“进程内工具”和“MCP 工具”。
6. 写端到端测试：Agent → MCP Client → MCP Server → Mock Provider。

**验收**：不修改规划领域逻辑即可切换工具传输方式；MCP Server 单独启动和测试。

**建议提交**：`feat: expose travel tools through mcp`

### 阶段 12：可观察性与 Agent Evaluation

**学习目标**：用数据回答“Agent 到底有没有变好”。

**公开 Trace 事件**应包括节点开始/结束、工具名、耗时、数据数量、约束结果、版本变化；不要展示隐藏思维链，也不要记录 API Key 或敏感原始响应。

**离线评估集**至少包含 20 个固定案例：

- 正常 3/5/7 日旅行。
- 极低预算。
- 雨天或连续雨天。
- 周一闭馆。
- 路线跨度过大。
- 严格步行上限。
- 晚出发。
- 删除固定景点。
- 相互冲突的用户要求。
- 工具超时、缺字段和部分失败。

**建议指标**：

| 指标 | 计算方式 |
|---|---|
| 硬约束通过率 | 最终无 error 的案例数 / 总案例数 |
| 事实引用率 | 行程地点中能追溯到工具数据的比例 |
| 预算误差 | 展示总额与明细求和的差值 |
| 重规划保留率 | 未受影响活动中保持不变的比例 |
| 工具成功率 | 成功工具调用 / 总调用 |
| 平均规划耗时 | 每个 run 的端到端时长 |
| 平均调用成本 | 每次规划的模型和 API 成本 |
| 无解识别率 | 冲突案例中正确拒绝的比例 |

**回归门槛建议**：硬约束通过率和预算正确率必须为 100%；其余指标先建立基线，再逐步提升。

**验收**：每次更改 Prompt、模型、规则或 Provider 后能运行同一套 eval，并看到前后差异。

**建议提交**：`test: add agent evaluation suite and tracing`

### 阶段 13：导出、安全与部署

**学习目标**：把演示原型变成可重复部署的应用。

**实施步骤**：

1. 先实现服务器端 Markdown 导出，再基于打印样式或服务端渲染做 PDF。
2. 增加输入长度限制、API 限流、CORS 白名单和通用安全响应头。
3. 对日志中的反馈文本和位置数据做最小化记录。
4. 将数据库、后端、前端分别容器化；本地用 Compose 联调。
5. 设置生产环境迁移、健康检查和回滚步骤。
6. 部署后跑一遍固定 smoke test。

**验收**：一个全新环境可根据文档部署；密钥不进入镜像和仓库；导出的金额、日期、地点与当前计划版本一致。

**建议提交**：`chore: harden export and deployment`

## 7. 数据库草图

先以最小字段开始，避免过早正规化所有 JSON：

```text
trips
- id UUID PK
- status
- destination_timezone
- request_json
- current_plan_version nullable
- created_at / updated_at

plan_versions
- id UUID PK
- trip_id FK
- version integer
- parent_version nullable
- itinerary_json
- constraint_report_json
- change_summary
- created_by enum(system, user_feedback)
- created_at

user_feedback
- id UUID PK
- trip_id FK
- base_version
- raw_text
- parsed_operations_json
- created_at

planning_runs
- id UUID PK
- trip_id FK
- trigger enum(initial, feedback, data_change)
- status
- started_at / finished_at
- error_code nullable

planning_events
- id UUID PK
- run_id FK
- sequence
- event_type
- public_payload_json
- created_at
```

数据库是恢复与审计来源；Agent State 是一次工作流运行时的协调状态；二者相关但不应混为一个对象。

## 8. 规划算法的渐进实现

不要直接追求“最优”。建议依次完成：

1. **可行性**：时间、营业、交通、预算全部不冲突。
2. **局部合理**：同一区域聚类，减少折返。
3. **偏好匹配**：使用可解释评分选择地点。
4. **鲁棒性**：给交通和排队预留缓冲。
5. **动态性**：变化后尽量少改原计划。

一个可解释评分可从简单加权开始：

```text
score(place) =
  0.35 × preference_match
+ 0.20 × rating_normalized
+ 0.15 × weather_fit
+ 0.15 × distance_fit
+ 0.10 × budget_fit
+ 0.05 × diversity_bonus
```

权重先写入配置并记录理由。评估后再调整，避免把随意数字伪装成科学结论。

## 9. 测试策略

### 9.1 测试金字塔

- **单元测试最多**：模型校验、预算、规则、评分、Patch、影响分析。
- **集成测试适量**：Repository、API、Agent 图、MCP 契约。
- **端到端测试少而关键**：创建 → 规划 → 反馈 → 接受 → 导出。
- **离线 Eval 独立**：衡量 Agent 质量，不取代确定性测试。

### 9.2 必测不变量

- 所有 Activity 都属于旅行日期范围。
- 同一天活动不重叠。
- 相邻活动之间留足路线时间。
- 所有金额明细之和等于汇总。
- 最终计划没有 `severity=error` 的违反项。
- 所有真实 POI 都能追溯到工具响应。
- 新版本号单调递增且父版本正确。
- 重规划不修改被锁定且不受影响的活动。

### 9.3 外部 API 测试原则

- 单元测试不访问真实网络。
- 保存脱敏响应样例做 Adapter 测试。
- 用契约测试防止 Provider 字段变化悄悄破坏系统。
- 少量可选 smoke test 才访问真实服务，并与常规 CI 分开。

## 10. 贯穿全程的错误处理

统一错误分类：

- `VALIDATION_ERROR`：用户输入不合法。
- `CLARIFICATION_REQUIRED`：信息不足或反馈有歧义。
- `NO_FEASIBLE_PLAN`：约束组合无解。
- `TOOL_TEMPORARILY_UNAVAILABLE`：外部工具暂时失败。
- `TOOL_DATA_INCOMPLETE`：返回事实不足。
- `MODEL_OUTPUT_INVALID`：模型输出未通过 Schema。
- `PLANNING_LIMIT_REACHED`：修正循环达到上限。
- `VERSION_CONFLICT`：用户基于旧版本提交修改。

前端应告诉用户下一步能做什么，例如“放宽预算或缩短景点列表”，而不是只显示 500。

## 11. 建议开发节奏

如果业余时间每周投入 8～12 小时，可按以下节奏安排：

| 周次 | 目标 | 可演示成果 |
|---|---|---|
| 1 | 阶段 0～1 | 前后端通、领域模型可校验 |
| 2 | 阶段 2 | 规则引擎报告具体冲突 |
| 3 | 阶段 3～4 | Mock 数据生成可行行程，API 闭环 |
| 4 | 阶段 5 | 浏览器完成创建与查看草案 |
| 5 | 阶段 6 | LLM 解析反馈并受 Schema 约束 |
| 6 | 阶段 7 | 接入天气和 POI/路线真实数据 |
| 7 | 阶段 8 | LangGraph 可暂停、修正、恢复 |
| 8 | 阶段 9 | 局部动态重规划和版本 diff |
| 9 | 阶段 10～11 | 持久化并通过 MCP 调工具 |
| 10 | 阶段 12～13 | Eval、导出、部署和项目复盘 |

这是学习节奏，不是硬性工期。每周宁可少做一个功能，也要完成测试、复盘和可演示成果。

## 12. 每阶段学习记录模板

在 `docs/learning-log/` 下为每个阶段写一页：

```markdown
# 阶段 N：标题

## 我解决的问题
## 输入、输出和不变量
## 我做过的关键选择
## 为什么没有采用其他方案
## 遇到的 Bug 与根因
## 测试如何证明它工作
## 仍然不知道的事情
## 如果重做一次会怎样改
```

这份记录将直接转化为面试时可讲的工程判断，而不只是功能清单。

## 13. 每次提交前检查表

- [ ] 这一提交只表达一个清晰意图。
- [ ] 新逻辑有对应测试。
- [ ] 错误分支和边界值已覆盖。
- [ ] 没有 API Key、用户隐私或大段原始工具响应进入日志。
- [ ] 新依赖确实必要并已锁定。
- [ ] README/API 文档与行为一致。
- [ ] Mock 模式仍然可运行。
- [ ] 所有自动化检查通过。
- [ ] 能用一句话说明本次改变如何靠近 Agent 闭环。

## 14. 最终演示脚本

项目完成时，用一个连续故事展示价值：

1. 创建“南京出发、东京 5 日、2 人、10000 元、喜欢动漫和美食、少购物”的旅行。
2. 展示 Agent 查询天气、POI 和路线的公开事件。
3. 展示规则引擎发现某天雨天户外冲突，并自动修正。
4. 打开带时间轴、交通和预算的草案。
5. 输入“第二天我 11:30 才能出发，但仍想看日落”。
6. 展示结构化反馈、影响分析和只修改第二天的 diff。
7. 再输入“酒店之外每天最多走 8 公里”，观察全局约束变化。
8. 展示计划版本历史和某一次工具调用证据。
9. 接受最终方案并导出 Markdown/PDF。
10. 展示 Eval 报告，说明硬约束通过率、重规划保留率和成本。

这个脚本能清楚回答：为什么需要 Agent、哪些事交给 LLM、哪些事必须由程序保证，以及系统如何面对现实变化。

## 15. 现在应该从哪里开始

严格只做阶段 0，不要提前接真实 API 或写 LangGraph：

1. 初始化 Git，并补充 `.gitignore`，避免提交现有 `.venv` 和 `.idea`。
2. 创建最小 FastAPI 后端和 `/health`。
3. 创建最小 Next.js 前端并读取健康状态。
4. 写清启动、测试、格式检查命令。
5. 做到新环境可复现后提交第一个 commit。

然后进入阶段 1，先把东京样例的输入、天气、POI、路线和期望行程写成可校验数据。到阶段 3 之前不接 LLM；当确定性底座跑通后，你才能清楚看到模型究竟增加了什么能力，又带来了哪些风险。
