# TravelMind

TravelMind 是一个动态旅行规划 Agent。它会根据用户需求、实时信息、预算和行程约束生成旅行计划，并在天气变化或用户提出新要求后进行动态重规划。

当前仓库已完成 **阶段 1：领域模型与固定样例数据**。在阶段 0 工程基线上，后端已经具备旅行请求、天气、地点、路线与行程领域模型，以及可重复加载的东京固定样例和空白行程生成脚本；暂不包含数据库、规划算法、LangGraph、LLM、MCP 或真实旅行数据 API。

## 技术栈

### 前端

- Next.js 16
- React 19
- TypeScript 5
- pnpm 11

### 后端

- Python 3.12+
- FastAPI
- Pydantic Settings
- Uvicorn
- pytest
- Ruff

## 仓库结构

```text
TravelMind/
├─ backend/                   FastAPI 后端
│  ├─ app/
│  │  ├─ api/routes/         HTTP 路由
│  │  ├─ core/               配置等基础能力
│  │  ├─ domain/             阶段 1 领域模型
│  │  ├─ fixtures/           固定样例与统一加载器
│  │  ├─ scripts/            可执行教学脚本
│  │  └─ main.py             FastAPI 应用入口
│  ├─ tests/                 后端测试
│  ├─ .env.example           后端环境变量示例
│  └─ pyproject.toml         Python 项目与工具配置
├─ frontend/                  Next.js 前端
│  ├─ src/app/               App Router 页面
│  ├─ src/components/        页面组件
│  ├─ src/lib/api/           后端 API 调用封装
│  └─ .env.example           前端环境变量示例
├─ docs/                      产品、架构与 API 文档
└─ README.md
```

## 环境要求

开始前确认本机已安装：

```powershell
python --version
node --version
pnpm --version
```

推荐版本：

```text
Python 3.12+
Node.js 20+
pnpm 11+
```

后端 `pyproject.toml` 声明要求 Python 3.12 及以上。请不要使用更低版本创建后端虚拟环境。

## 第一次安装

### 1. 创建并安装后端环境

从项目根目录执行：

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
cd ..
```

如果 PowerShell 阻止执行激活脚本，可以仅为当前进程调整策略：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 2. 安装前端环境

```powershell
cd frontend
pnpm install --frozen-lockfile
Copy-Item .env.example .env.local
cd ..
```

## 环境变量

### 后端 `backend/.env`

```dotenv
TRAVELMIND_ENV=development
TRAVELMIND_API_HOST=127.0.0.1
TRAVELMIND_API_PORT=8000
TRAVELMIND_CORS_ORIGINS=http://localhost:3000
```

### 前端 `frontend/.env.local`

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

`.env` 和 `.env.local` 只用于本地环境，已被 Git 忽略。不要提交 API Key 或其他密钥；仓库只提交 `.env.example`。

## 启动开发环境

前后端需要在两个独立终端中运行。

### 终端一：启动后端

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

启动成功后可访问：

| 地址 | 用途 |
|---|---|
| <http://localhost:8000/health/live> | 进程存活检查 |
| <http://localhost:8000/health/ready> | 服务就绪检查 |
| <http://localhost:8000/docs> | Swagger UI |
| <http://localhost:8000/openapi.json> | OpenAPI 契约 |

### 终端二：启动前端

```powershell
cd frontend
pnpm dev
```

访问 <http://localhost:3000>。首页应显示 TravelMind 基本信息和后端健康状态。

## 运行检查

### 后端

```powershell
cd backend
.\.venv\Scripts\Activate.ps1

# 自动化测试
python -m pytest

# 静态检查
ruff check app tests

# 格式检查
ruff format --check app tests
```

如需自动格式化：

```powershell
ruff format app tests
```

格式化后仍需重新运行测试和静态检查。

### 前端

```powershell
cd frontend

# ESLint
pnpm lint

# 生产构建
pnpm build
```

生产构建不能依赖开发服务器已经启动。若构建因在线字体下载失败，应改用系统字体或项目内的本地字体，而不是跳过构建检查。

## 手工联调验证

完成自动化检查后，执行以下验证：

1. 启动 FastAPI，访问 `/health/live`，确认返回 `200`。
2. 访问 `/health/ready`，确认返回 `200`。
3. 访问 `/docs`，确认 OpenAPI 页面正常加载。
4. 启动 Next.js，访问首页。
5. 确认首页显示后端服务名和版本。
6. 停止 FastAPI 后刷新前端页面。
7. 确认前端显示“暂时无法连接后端服务”，而不是页面崩溃。

## 常用命令速查

### 后端

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
python -m pytest
ruff check app tests
ruff format --check app tests
python -m app.scripts.build_fixture_itinerary
```

### 前端

```powershell
cd frontend
pnpm dev
pnpm lint
pnpm build
pnpm start
```

## 常见问题

### 前端显示无法连接后端

依次确认：

1. FastAPI 是否运行在 `http://localhost:8000`。
2. `frontend/.env.local` 中的 `NEXT_PUBLIC_API_BASE_URL` 是否正确。
3. 修改 `.env.local` 后是否重启了 Next.js 开发服务器。
4. `backend/.env` 中是否允许 `http://localhost:3000` 作为 CORS Origin。

### 后端无法导入 `app`

确认当前工作目录是 `backend`，然后执行：

```powershell
uvicorn app.main:app --reload --port 8000
```

### Python 版本不符合要求

检查虚拟环境的实际版本：

```powershell
cd backend
.\.venv\Scripts\python.exe --version
```

如果低于 3.12，请使用 Python 3.12 重新创建 `backend/.venv`。虚拟环境是本地生成物，不应提交到 Git。

### PowerShell 找不到 `pnpm`

如果已经安装 Node.js，可通过 Corepack 启用项目声明的包管理器：

```powershell
corepack enable
corepack prepare pnpm@11.0.8 --activate
pnpm --version
```

## 阶段 0 验收标准

全部满足后才能进入阶段 1：

- [ ] 使用 Python 3.12+ 创建后端虚拟环境。
- [ ] 后端可以通过一条命令启动。
- [ ] `/health/live` 返回 `200`。
- [ ] `/health/ready` 返回 `200`。
- [ ] `/docs` 和 `/openapi.json` 可访问。
- [ ] `python -m pytest` 全部通过。
- [ ] `ruff check app tests` 通过。
- [ ] `ruff format --check app tests` 通过。
- [ ] 前端可以通过一条命令启动。
- [ ] `pnpm lint` 通过。
- [ ] `pnpm build` 通过。
- [ ] 前端能够显示后端健康状态。
- [ ] 后端停止时前端显示明确失败状态。
- [ ] `.env`、`.env.local`、`.venv`、`node_modules` 和 `.next` 未进入 Git。
- [ ] 仓库中不存在真实密钥。
- [ ] 新开发者只按照本 README 就能完成安装、启动和验证。

## 阶段 1 验收结果

- [x] 领域模型不依赖 Web、数据库、Agent 或 Provider SDK。
- [x] 合法、非法和边界输入均有自动化测试。
- [x] 东京样例包含 5 天天气、10 个 POI 和 20 条有向路线。
- [x] 样例覆盖室内、户外、mixed、预约和闭馆差异。
- [x] 空白行程脚本输出连续 5 天的合法 JSON，并可由 `Itinerary` 再次读取。
- [x] 后端测试、Ruff、前端 lint 和前端生产构建均通过。

详细步骤与完整清单见 [阶段 1 教程](docs/阶段1-领域模型与固定样例数据教程.md)。

## 项目文档

- [项目说明](docs/项目说明.md)
- [详细实现计划](docs/TravelMind-详细实现计划.md)
- [API 与对象契约](docs/api-contract.md)
- [阶段 1：领域模型与固定样例数据教程](docs/阶段1-领域模型与固定样例数据教程.md)
- [阶段 2：确定性约束引擎教程](docs/阶段2-确定性约束引擎教程.md)
- [前端参考渲染图提示词](docs/image2-前端页面渲染提示词.md)

## 当前不包含的能力

以下内容不属于阶段 1：

- 数据库和迁移
- 规划算法与约束引擎
- 天气、POI 与路线 Provider
- LLM 和 Tool Calling
- LangGraph 工作流
- 动态重规划
- MCP Server
- 登录、权限和生产部署

这些能力会按照详细实现计划逐阶段加入。
