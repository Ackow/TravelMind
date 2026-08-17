# 阶段 4 教程：用 FastAPI 暴露旅行规划 REST API

> 目标：把阶段 1 的领域对象、阶段 2 的约束引擎和阶段 3 的确定性规划器，封装成一组边界清晰、错误稳定、可测试的 HTTP 接口。
> 本阶段使用内存 Repository 和东京固定事实；不接数据库、真实 Provider、LLM、LangGraph、后台任务队列或真正的 SSE。

---

## 1. 完成后应该得到什么

阶段 4 完成时，应该可以只使用 HTTP 客户端完成下面的纵向流程：

~~~text
创建旅行
→ 启动规划运行
→ 查询规划运行
→ 查看第 1 版计划
→ 提交结构化反馈
→ 自动生成第 2 版计划
→ 查看公开规划事件
~~~

本教程实现以下接口：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | /api/v1/trips | 创建旅行 |
| GET | /api/v1/trips/{trip_id} | 获取旅行 |
| POST | /api/v1/trips/{trip_id}/planning-runs | 启动规划 |
| GET | /api/v1/trips/{trip_id}/planning-runs/{run_id} | 获取运行状态 |
| GET | /api/v1/trips/{trip_id}/planning-runs/{run_id}/events | 获取公开事件 |
| GET | /api/v1/trips/{trip_id}/plans | 获取版本列表 |
| GET | /api/v1/trips/{trip_id}/plans/{version} | 获取完整版本；支持 current |
| POST | /api/v1/trips/{trip_id}/feedback | 提交结构化反馈并重规划 |

### 为什么不用总计划里的 POST /trips/{id}/plan

详细实现计划写于较早时期。当前权威契约 docs/api-contract.md 已将耗时操作统一建模为 PlanningRun，因此本教程使用：

~~~text
POST /api/v1/trips/{trip_id}/planning-runs
~~~

即使本阶段内部同步完成规划，HTTP 仍返回 202 和 PlanningRun。以后换成队列任务时，前端契约不需要推倒重写。

### 本阶段反馈的边界

自然语言解析属于后续 LLM/Agent 阶段。本阶段只执行前端已经结构化的四类操作：

- set_budget；
- set_max_walking；
- add_required_place；
- add_excluded_place。

如果只传 message、没有 client_operations，接口返回“需要澄清”，不会假装理解自然语言。这样可以先验证版本化重规划链路，又不会把关键词匹配伪装成 Agent。

---

## 2. 先理解四层边界

~~~text
HTTP / FastAPI 路由
        ↓
API DTO：请求、响应、错误
        ↓
Application Service：创建、规划、反馈等用例
        ↓
Repository + Facts Factory + 阶段 1～3 领域能力
~~~

每层职责：

| 层 | 可以做什么 | 不应该做什么 |
| --- | --- | --- |
| 路由 | 解析 Header/Path/Body，调用用例，选择 HTTP 状态码 | 写规划算法、直接操作字典仓库 |
| API DTO | 描述客户端可提交和服务端返回的字段 | 混入第三方 SDK 对象 |
| Application | 编排创建、规划、版本化、状态迁移 | 依赖 FastAPI Request/Response |
| Infrastructure | 内存存储、固定事实适配 | 决定 HTTP 状态码 |
| Domain / Planning | 校验领域对象、检查约束、生成行程 | 导入 FastAPI、Repository |

最重要的依赖方向：

~~~text
api → application → domain/planning
                  → repository protocol
infrastructure → repository protocol
~~~

domain 和 planning 不能反向导入 API。

---

## 3. 文件清单

创建以下文件：

~~~text
backend/app/
├─ api/
│  ├─ __init__.py
│  ├─ dependencies.py
│  ├─ errors.py
│  ├─ mappers.py
│  ├─ router.py
│  ├─ schemas.py
│  └─ routes/
│     ├─ __init__.py
│     ├─ feedback.py
│     ├─ health.py                 已存在
│     ├─ planning.py
│     ├─ plans.py
│     └─ trips.py
├─ application/
│  ├─ __init__.py
│  ├─ clock.py
│  ├─ errors.py
│  ├─ facts.py
│  ├─ models.py
│  ├─ repository.py
│  └─ service.py
├─ infrastructure/
│  ├─ __init__.py
│  └─ memory_repository.py
└─ main.py                         修改

backend/tests/api/
├─ __init__.py
├─ conftest.py
├─ test_errors.py
├─ test_feedback_flow.py
├─ test_openapi.py
└─ test_trip_planning_flow.py
~~~

不要创建一个几千行的 routes.py。路由按资源拆分，业务编排集中在 Application Service。

---

## 4. API DTO：客户端能写什么，服务端返回什么

创建 backend/app/api/schemas.py：

~~~python
from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.application.models import (
    PlanStatus,
    PlanTrigger,
    PlanningEventType,
    PlanningRunStatus,
    PlanningRunTrigger,
    TripStatus,
)
from app.domain.common import DateRange, Money
from app.domain.constraints import ConstraintReport
from app.domain.itinerary import Itinerary
from app.domain.trip import TripConstraints, TripPreferences, TripRequest


class ApiModel(BaseModel):
    """所有 HTTP DTO 的共同配置。"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class TripCreateRequest(TripRequest):
    """创建旅行请求。

    它和领域 TripRequest 当前字段相同，但拥有独立的 OpenAPI Schema 名称。
    客户端无法提交 id、status、revision 或 current_plan_version。
    """


class TripResponse(ApiModel):
    id: UUID
    status: TripStatus
    revision: int = Field(ge=1)
    origin: str
    destination: str
    destination_timezone: str
    date_range: DateRange
    travelers: int
    preferences: TripPreferences
    constraints: TripConstraints
    locale: str
    display_currency: str
    notes: str | None
    current_plan_version: int | None
    active_planning_run_id: UUID | None
    created_at: datetime
    updated_at: datetime


class StartPlanningRequest(ApiModel):
    mode: Literal["initial", "regenerate"] = "initial"
    force_refresh_tools: bool = False
    max_repair_attempts: int = Field(default=3, ge=1, le=5)


class PlanningRunResponse(ApiModel):
    id: UUID
    trip_id: UUID
    trigger: PlanningRunTrigger
    status: PlanningRunStatus
    progress_percent: int = Field(ge=0, le=100)
    current_step: str | None
    base_plan_version: int | None
    result_plan_version: int | None
    feedback_id: UUID | None
    repair_attempts: int = Field(ge=0)
    max_repair_attempts: int = Field(ge=0)
    error: dict[str, object] | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class StartPlanningResponse(ApiModel):
    planning_run: PlanningRunResponse
    events_url: str


class PlanVersionResponse(ApiModel):
    id: UUID
    trip_id: UUID
    version: int = Field(ge=1)
    parent_version: int | None
    status: PlanStatus
    itinerary: Itinerary
    constraint_report: ConstraintReport
    change_summary: str
    trigger: PlanTrigger
    planning_run_id: UUID
    created_at: datetime
    accepted_at: datetime | None


class PlanVersionSummary(ApiModel):
    id: UUID
    trip_id: UUID
    version: int
    parent_version: int | None
    status: PlanStatus
    day_count: int
    planned_total: Money
    error_count: int
    warning_count: int
    change_summary: str
    trigger: PlanTrigger
    planning_run_id: UUID
    created_at: datetime


class PlanListResponse(ApiModel):
    items: list[PlanVersionSummary]


class PlanningEventResponse(ApiModel):
    id: str
    run_id: UUID
    sequence: int = Field(ge=1)
    type: PlanningEventType
    step: str | None
    message: str
    payload: dict[str, object]
    created_at: datetime


class PlanningEventListResponse(ApiModel):
    items: list[PlanningEventResponse]


class SetBudgetOperation(ApiModel):
    op: Literal["set_budget"]
    total_budget: Money
    hard_limit: bool
    reason: str | None = Field(default=None, max_length=500)


class SetMaxWalkingOperation(ApiModel):
    op: Literal["set_max_walking"]
    meters_per_day: int = Field(ge=1000, le=50000)
    reason: str | None = Field(default=None, max_length=500)


class AddRequiredPlaceOperation(ApiModel):
    op: Literal["add_required_place"]
    place_name: str = Field(min_length=1, max_length=200)
    reason: str | None = Field(default=None, max_length=500)


class AddExcludedPlaceOperation(ApiModel):
    op: Literal["add_excluded_place"]
    place_name: str = Field(min_length=1, max_length=200)
    reason: str | None = Field(default=None, max_length=500)


FeedbackOperation = Annotated[
    SetBudgetOperation
    | SetMaxWalkingOperation
    | AddRequiredPlaceOperation
    | AddExcludedPlaceOperation,
    Field(discriminator="op"),
]


class FeedbackCreateRequest(ApiModel):
    base_plan_version: int = Field(ge=1)
    message: str = Field(min_length=1, max_length=2000)
    client_operations: list[FeedbackOperation] = Field(default_factory=list)
    auto_start_replanning: bool = True


class FeedbackScope(ApiModel):
    dates: list[date] = Field(default_factory=list)
    activity_ids: list[UUID] = Field(default_factory=list)
    global_: bool = Field(default=True, alias="global")

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )


class FeedbackRecordResponse(ApiModel):
    id: UUID
    trip_id: UUID
    base_plan_version: int
    message: str
    operations: list[FeedbackOperation]
    scope: FeedbackScope
    requires_clarification: bool
    clarification_question: str | None
    planning_run_id: UUID | None
    created_at: datetime


class FeedbackResponse(ApiModel):
    feedback: FeedbackRecordResponse
    planning_run: PlanningRunResponse | None
    events_url: str | None
~~~

### 为什么 TripCreateRequest 和 TripResponse 必须分开

如果创建接口直接接收 TripResponse，客户端就能伪造：

- id；
- status；
- revision；
- current_plan_version；
- created_at。

请求 DTO 只表达“用户允许提交的字段”，响应 DTO 才包含服务端生成字段。这正是 API 边界。

### 为什么暂时继承 TripRequest

当前创建请求和领域请求字段完全一致，继承可以避免复制一份容易漂移的字段定义，同时 OpenAPI 仍生成 TripCreateRequest 名称。

如果以后出现差异，例如 API 允许 destination_timezone 为空而领域层要求已经解析完成，就应改为显式 DTO，并增加 to_domain() 映射。不要为了复用而破坏两层语义。

---

## 5. 应用层内部记录

创建 backend/app/application/models.py：

~~~python
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.constraints import ConstraintReport
from app.domain.itinerary import Itinerary
from app.domain.trip import TripRequest


class ApplicationModel(BaseModel):
    """应用层记录也禁止悄悄接受未知字段。"""

    model_config = ConfigDict(extra="forbid")


class TripStatus(StrEnum):
    DRAFT = "draft"
    PLANNING = "planning"
    NEEDS_REVIEW = "needs_review"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class PlanningRunStatus(StrEnum):
    QUEUED = "queued"
    RESEARCHING = "researching"
    PLANNING = "planning"
    VALIDATING = "validating"
    REPAIRING = "repairing"
    WAITING_FOR_REVIEW = "waiting_for_review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PlanningRunTrigger(StrEnum):
    INITIAL = "initial"
    FEEDBACK = "feedback"
    DATA_CHANGE = "data_change"


class PlanStatus(StrEnum):
    DRAFT = "draft"
    VALID = "valid"
    ACCEPTED = "accepted"
    SUPERSEDED = "superseded"


class PlanTrigger(StrEnum):
    INITIAL = "initial"
    USER_FEEDBACK = "user_feedback"
    DATA_CHANGE = "data_change"
    MANUAL_VALIDATION = "manual_validation"


class PlanningEventType(StrEnum):
    RUN_STARTED = "run_started"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    CONSTRAINT_FOUND = "constraint_found"
    REPAIR_STARTED = "repair_started"
    PLAN_CREATED = "plan_created"
    REVIEW_REQUIRED = "review_required"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"


class TripRecord(ApplicationModel):
    id: UUID
    status: TripStatus
    revision: int = Field(ge=1)
    request: TripRequest
    current_plan_version: int | None = None
    active_planning_run_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class PlanningRunRecord(ApplicationModel):
    id: UUID
    trip_id: UUID
    trigger: PlanningRunTrigger
    status: PlanningRunStatus
    progress_percent: int = Field(ge=0, le=100)
    current_step: str | None = None
    base_plan_version: int | None = None
    result_plan_version: int | None = None
    feedback_id: UUID | None = None
    repair_attempts: int = Field(ge=0)
    max_repair_attempts: int = Field(ge=0)
    error: dict[str, object] | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class PlanVersionRecord(ApplicationModel):
    id: UUID
    trip_id: UUID
    version: int = Field(ge=1)
    parent_version: int | None
    status: PlanStatus
    itinerary: Itinerary
    constraint_report: ConstraintReport
    change_summary: str
    trigger: PlanTrigger
    planning_run_id: UUID
    created_at: datetime
    accepted_at: datetime | None = None


class PlanningEventRecord(ApplicationModel):
    id: str
    run_id: UUID
    sequence: int = Field(ge=1)
    type: PlanningEventType
    step: str | None
    message: str
    payload: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class FeedbackRecord(ApplicationModel):
    id: UUID
    trip_id: UUID
    base_plan_version: int
    message: str
    operations: list[dict[str, object]]
    affected_dates: list[date] = Field(default_factory=list)
    affected_activity_ids: list[UUID] = Field(default_factory=list)
    global_scope: bool = True
    requires_clarification: bool
    clarification_question: str | None
    planning_run_id: UUID | None
    created_at: datetime
~~~

这些记录不是领域模型：

- TripRecord 表示资源生命周期；
- PlanningRunRecord 表示一次用例执行；
- PlanVersionRecord 保存不可变行程快照；
- PlanningEventRecord 只保存可公开进度；
- FeedbackRecord 保存用户输入和结构化操作。

不要把 status、revision、HTTP 资源版本硬塞进 TripRequest。

---

## 6. 时钟接口：测试不能依赖现在几点

创建 backend/app/application/clock.py：

~~~python
from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """返回带时区的当前时间。"""


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """测试使用的固定时钟。"""

    def __init__(self, value: datetime) -> None:
        if value.tzinfo is None:
            raise ValueError("fixed clock value must be timezone-aware")
        self._value = value

    def now(self) -> datetime:
        return self._value
~~~

阶段 3 规划器不能读取系统时间；应用层可以读取，但必须通过 Clock 注入，再把时间放进 PlanningFacts。

---

## 7. Repository 协议

创建 backend/app/application/repository.py：

~~~python
from typing import Protocol
from uuid import UUID

from app.application.models import (
    FeedbackRecord,
    PlanningEventRecord,
    PlanningRunRecord,
    PlanVersionRecord,
    TripRecord,
)


class TravelRepository(Protocol):
    """应用层需要的存储能力，不暴露字典或数据库细节。"""

    def add_trip(self, trip: TripRecord) -> None: ...

    def get_trip(self, trip_id: UUID) -> TripRecord | None: ...

    def save_trip(self, trip: TripRecord) -> None: ...

    def add_run(self, run: PlanningRunRecord) -> None: ...

    def get_run(self, trip_id: UUID, run_id: UUID) -> PlanningRunRecord | None: ...

    def save_run(self, run: PlanningRunRecord) -> None: ...

    def add_plan(self, plan: PlanVersionRecord) -> None: ...

    def save_plan(self, plan: PlanVersionRecord) -> None: ...

    def get_plan(self, trip_id: UUID, version: int) -> PlanVersionRecord | None: ...

    def list_plans(self, trip_id: UUID) -> list[PlanVersionRecord]: ...

    def add_event(self, event: PlanningEventRecord) -> None: ...

    def list_events(self, run_id: UUID) -> list[PlanningEventRecord]: ...

    def add_feedback(self, feedback: FeedbackRecord) -> None: ...
~~~

Application Service 只依赖这个 Protocol。阶段 5 换 PostgreSQL 时，服务代码不需要知道 SQLAlchemy 的 Session。

---

## 8. 内存 Repository

创建 backend/app/infrastructure/memory_repository.py：

~~~python
from threading import RLock
from uuid import UUID

from app.application.models import (
    FeedbackRecord,
    PlanningEventRecord,
    PlanningRunRecord,
    PlanVersionRecord,
    TripRecord,
)


class InMemoryTravelRepository:
    """适合单进程教学和测试的线程安全内存仓库。

    所有读写都使用 deep copy，防止调用方绕过 save 方法原地修改仓库内容。
    """

    def __init__(self) -> None:
        self._trips: dict[UUID, TripRecord] = {}
        self._runs: dict[tuple[UUID, UUID], PlanningRunRecord] = {}
        self._plans: dict[tuple[UUID, int], PlanVersionRecord] = {}
        self._events: dict[UUID, list[PlanningEventRecord]] = {}
        self._feedback: dict[UUID, FeedbackRecord] = {}
        self._lock = RLock()

    @staticmethod
    def _copy(value):
        return value.model_copy(deep=True)

    def add_trip(self, trip: TripRecord) -> None:
        with self._lock:
            if trip.id in self._trips:
                raise ValueError("trip already exists")
            self._trips[trip.id] = self._copy(trip)

    def get_trip(self, trip_id: UUID) -> TripRecord | None:
        with self._lock:
            value = self._trips.get(trip_id)
            return None if value is None else self._copy(value)

    def save_trip(self, trip: TripRecord) -> None:
        with self._lock:
            if trip.id not in self._trips:
                raise ValueError("trip does not exist")
            self._trips[trip.id] = self._copy(trip)

    def add_run(self, run: PlanningRunRecord) -> None:
        with self._lock:
            key = (run.trip_id, run.id)
            if key in self._runs:
                raise ValueError("planning run already exists")
            self._runs[key] = self._copy(run)

    def get_run(self, trip_id: UUID, run_id: UUID) -> PlanningRunRecord | None:
        with self._lock:
            value = self._runs.get((trip_id, run_id))
            return None if value is None else self._copy(value)

    def save_run(self, run: PlanningRunRecord) -> None:
        with self._lock:
            key = (run.trip_id, run.id)
            if key not in self._runs:
                raise ValueError("planning run does not exist")
            self._runs[key] = self._copy(run)

    def add_plan(self, plan: PlanVersionRecord) -> None:
        with self._lock:
            key = (plan.trip_id, plan.version)
            if key in self._plans:
                raise ValueError("plan version already exists")
            self._plans[key] = self._copy(plan)

    def save_plan(self, plan: PlanVersionRecord) -> None:
        with self._lock:
            key = (plan.trip_id, plan.version)
            if key not in self._plans:
                raise ValueError("plan version does not exist")
            self._plans[key] = self._copy(plan)

    def get_plan(self, trip_id: UUID, version: int) -> PlanVersionRecord | None:
        with self._lock:
            value = self._plans.get((trip_id, version))
            return None if value is None else self._copy(value)

    def list_plans(self, trip_id: UUID) -> list[PlanVersionRecord]:
        with self._lock:
            values = [
                self._copy(plan)
                for (known_trip_id, _), plan in self._plans.items()
                if known_trip_id == trip_id
            ]
        return sorted(values, key=lambda item: item.version)

    def add_event(self, event: PlanningEventRecord) -> None:
        with self._lock:
            self._events.setdefault(event.run_id, []).append(self._copy(event))

    def list_events(self, run_id: UUID) -> list[PlanningEventRecord]:
        with self._lock:
            return [self._copy(item) for item in self._events.get(run_id, [])]

    def add_feedback(self, feedback: FeedbackRecord) -> None:
        with self._lock:
            if feedback.id in self._feedback:
                raise ValueError("feedback already exists")
            self._feedback[feedback.id] = self._copy(feedback)
~~~

### 内存仓库的限制

- 服务重启后数据消失；
- 多进程 worker 不共享数据；
- 没有真正事务；
- 不适合生产。

这不是缺陷隐藏，而是阶段边界。它让我们先验证 API、用例和版本语义，下一阶段再替换持久化实现。

---

## 9. 应用错误和 HTTP 错误映射

Application Service 不应抛 HTTPException，因为它不属于 FastAPI。先创建 backend/app/application/errors.py：

~~~python
from dataclasses import dataclass, field


@dataclass(slots=True)
class ApplicationError(Exception):
    code: str
    message: str
    status_code: int
    details: list[dict[str, object]] = field(default_factory=list)
    retryable: bool = False
~~~

创建 backend/app/api/errors.py：

~~~python
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.application.errors import ApplicationError


def error_body(
    *,
    request: Request,
    code: str,
    message: str,
    details: list[dict[str, object]],
    retryable: bool,
) -> dict[str, object]:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
            "retryable": retryable,
        }
    }


async def application_error_handler(
    request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(
            request=request,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            retryable=exc.retryable,
        ),
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(part) for part in item["loc"]),
            "reason": item["type"],
            "message": item["msg"],
        }
        for item in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_body(
            request=request,
            code="VALIDATION_ERROR",
            message="请求参数不合法",
            details=details,
            retryable=False,
        ),
    )


def install_error_handlers(application: FastAPI) -> None:
    application.add_exception_handler(
        ApplicationError,
        application_error_handler,
    )
    application.add_exception_handler(
        RequestValidationError,
        validation_error_handler,
    )
~~~

路由、应用层和错误响应之间的关系：

~~~text
ApplicationError("TRIP_NOT_FOUND", ..., 404)
        ↓ API handler
HTTP 404
{"error": {"code": "TRIP_NOT_FOUND", ...}}
~~~

客户端判断错误必须读取 code，不能解析中文 message。
+---

## 10. 固定事实工厂：连接 API 请求和阶段 3

不要让 Application Service 导入 scripts/generate_fixture_plan.py。scripts 是命令行入口，不是可复用应用依赖。

创建 backend/app/application/facts.py：

~~~python
from datetime import datetime, timedelta

from app.application.errors import ApplicationError
from app.domain.common import DataQuality, SourceRef
from app.domain.itinerary import ExchangeRate
from app.domain.trip import TripRequest
from app.fixtures.loader import (
    load_tokyo_places,
    load_tokyo_route_matrix,
    load_tokyo_weather,
)
from app.planning import PlanningFacts


class FixturePlanningFactsFactory:
    """把当前旅行需求与阶段 1 东京事实组合成 PlanningFacts。

    阶段 4 只支持东京固定样例。真实天气、POI 和路线 Provider 属于后续阶段。
    """

    def build(
        self,
        *,
        request: TripRequest,
        planned_at: datetime,
    ) -> PlanningFacts:
        if request.destination.casefold() not in {"东京", "tokyo"}:
            raise ApplicationError(
                code="TOOL_DATA_INCOMPLETE",
                message="阶段 4 固定事实只支持东京",
                status_code=502,
                retryable=False,
            )

        weather = tuple(load_tokyo_weather())
        expected_dates = tuple(
            request.date_range.start_date + timedelta(days=offset)
            for offset in range(request.date_range.day_count)
        )
        fixture_dates = tuple(item.date for item in weather)
        if expected_dates != fixture_dates:
            raise ApplicationError(
                code="TOOL_DATA_INCOMPLETE",
                message="请求日期不在东京固定天气样例范围内",
                status_code=502,
                details=[
                    {
                        "expected_dates": [item.isoformat() for item in fixture_dates],
                        "actual_dates": [item.isoformat() for item in expected_dates],
                    }
                ],
                retryable=False,
            )

        if request.display_currency == "JPY":
            rates: dict[str, ExchangeRate] = {}
        elif request.display_currency == "CNY":
            source = SourceRef(
                provider="mock",
                source_id="jpy-cny-stage-4",
                fetched_at=planned_at,
                data_quality=DataQuality.MOCK,
            )
            rates = {
                "JPY/CNY": ExchangeRate(
                    from_currency="JPY",
                    to_currency="CNY",
                    rate=4.8,
                    fetched_at=planned_at,
                    source=source,
                )
            }
        else:
            raise ApplicationError(
                code="TOOL_DATA_INCOMPLETE",
                message="固定样例缺少目标币种汇率",
                status_code=502,
                details=[{"currency": request.display_currency}],
                retryable=False,
            )

        return PlanningFacts(
            request=request,
            places=tuple(load_tokyo_places()),
            weather=weather,
            route_matrix=load_tokyo_route_matrix(),
            exchange_rates=rates,
            planned_at=planned_at,
        )
~~~

为什么必须由工厂组合：

- TripRequest 来自当前 API 资源，不应继续使用 fixture 中的旧请求；
- 地点、天气、路线和汇率来自固定事实；
- planned_at 由应用时钟传入；
- 将来换真实 Provider 时，只替换 Facts Factory 或上层研究流程。

---

## 11. Application Service：真正的用例编排

创建 backend/app/application/service.py：

~~~python
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.application.clock import Clock
from app.application.errors import ApplicationError
from app.application.facts import FixturePlanningFactsFactory
from app.application.models import (
    FeedbackRecord,
    PlanningEventRecord,
    PlanningEventType,
    PlanningRunRecord,
    PlanningRunStatus,
    PlanningRunTrigger,
    PlanStatus,
    PlanTrigger,
    PlanVersionRecord,
    TripRecord,
    TripStatus,
)
from app.application.repository import TravelRepository
from app.domain.itinerary import Itinerary
from app.domain.trip import TripRequest
from app.planning import DeterministicPlanner, PlannerConfig, PlanningStatus


class TravelService:
    """阶段 4 的应用用例入口。路由不直接读写 Repository。"""

    def __init__(
        self,
        *,
        repository: TravelRepository,
        clock: Clock,
        facts_factory: FixturePlanningFactsFactory,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._facts_factory = facts_factory

    def create_trip(self, request: TripRequest) -> TripRecord:
        now = self._clock.now()
        trip = TripRecord(
            id=uuid4(),
            status=TripStatus.DRAFT,
            revision=1,
            request=request,
            current_plan_version=None,
            active_planning_run_id=None,
            created_at=now,
            updated_at=now,
        )
        self._repository.add_trip(trip)
        return trip

    def get_trip(self, trip_id: UUID) -> TripRecord:
        trip = self._repository.get_trip(trip_id)
        if trip is None or trip.status == TripStatus.ARCHIVED:
            raise ApplicationError(
                code="TRIP_NOT_FOUND",
                message="旅行不存在",
                status_code=404,
            )
        return trip

    def get_run(self, trip_id: UUID, run_id: UUID) -> PlanningRunRecord:
        self.get_trip(trip_id)
        run = self._repository.get_run(trip_id, run_id)
        if run is None:
            raise ApplicationError(
                code="RUN_NOT_FOUND",
                message="规划运行不存在",
                status_code=404,
            )
        return run

    def list_events(
        self,
        trip_id: UUID,
        run_id: UUID,
    ) -> list[PlanningEventRecord]:
        self.get_run(trip_id, run_id)
        return self._repository.list_events(run_id)

    def list_plans(self, trip_id: UUID) -> list[PlanVersionRecord]:
        self.get_trip(trip_id)
        return self._repository.list_plans(trip_id)

    def get_plan(
        self,
        trip_id: UUID,
        version: int | str,
    ) -> PlanVersionRecord:
        trip = self.get_trip(trip_id)
        if version == "current":
            if trip.current_plan_version is None:
                raise ApplicationError(
                    code="PLAN_NOT_FOUND",
                    message="旅行尚未生成计划",
                    status_code=404,
                )
            resolved_version = trip.current_plan_version
        else:
            try:
                resolved_version = int(version)
            except ValueError as exc:
                raise ApplicationError(
                    code="PLAN_NOT_FOUND",
                    message="计划版本格式不正确",
                    status_code=404,
                ) from exc

        plan = self._repository.get_plan(trip_id, resolved_version)
        if plan is None:
            raise ApplicationError(
                code="PLAN_NOT_FOUND",
                message="计划版本不存在",
                status_code=404,
            )
        return plan

    def start_planning(
        self,
        *,
        trip_id: UUID,
        max_repair_attempts: int,
    ) -> PlanningRunRecord:
        return self._execute_plan(
            trip=self.get_trip(trip_id),
            run_id=uuid4(),
            trigger=PlanningRunTrigger.INITIAL,
            feedback_id=None,
            max_repair_attempts=max_repair_attempts,
        )

    def submit_feedback(
        self,
        *,
        trip_id: UUID,
        base_plan_version: int,
        message: str,
        operations: list[dict[str, object]],
        auto_start_replanning: bool,
    ) -> tuple[FeedbackRecord, PlanningRunRecord | None]:
        trip = self.get_trip(trip_id)
        if trip.current_plan_version != base_plan_version:
            raise ApplicationError(
                code="VERSION_CONFLICT",
                message="反馈基于的计划版本已经过期",
                status_code=409,
                details=[
                    {
                        "base_plan_version": base_plan_version,
                        "current_plan_version": trip.current_plan_version,
                    }
                ],
            )

        feedback_id = uuid4()
        now = self._clock.now()
        if not operations:
            feedback = FeedbackRecord(
                id=feedback_id,
                trip_id=trip.id,
                base_plan_version=base_plan_version,
                message=message,
                operations=[],
                affected_dates=[],
                affected_activity_ids=[],
                global_scope=True,
                requires_clarification=True,
                clarification_question="请明确选择要修改的预算、步行上限或地点约束。",
                planning_run_id=None,
                created_at=now,
            )
            self._repository.add_feedback(feedback)
            return feedback, None

        updated_request = self._apply_operations(
            request=trip.request,
            operations=operations,
        )
        run_id = uuid4() if auto_start_replanning else None
        updated_trip = trip.model_copy(
            update={
                "request": updated_request,
                "status": (
                    TripStatus.REPLANNING
                    if run_id is not None
                    else TripStatus.NEEDS_REVIEW
                ),
                "revision": trip.revision + 1,
                "updated_at": now,
            }
        )
        self._repository.save_trip(updated_trip)

        feedback = FeedbackRecord(
            id=feedback_id,
            trip_id=trip.id,
            base_plan_version=base_plan_version,
            message=message,
            operations=operations,
            affected_dates=[],
            affected_activity_ids=[],
            global_scope=True,
            requires_clarification=False,
            clarification_question=None,
            planning_run_id=run_id,
            created_at=now,
        )
        self._repository.add_feedback(feedback)
        if run_id is None:
            return feedback, None

        run = self._execute_plan(
            trip=updated_trip,
            run_id=run_id,
            trigger=PlanningRunTrigger.FEEDBACK,
            feedback_id=feedback_id,
            max_repair_attempts=3,
        )
        return feedback, run

    def _apply_operations(
        self,
        *,
        request: TripRequest,
        operations: list[dict[str, object]],
    ) -> TripRequest:
        data = request.model_dump(mode="python")
        constraints = data["constraints"]

        for operation in operations:
            op = operation["op"]
            if op == "set_budget":
                constraints["total_budget"] = operation["total_budget"]
                constraints["budget_is_hard_limit"] = operation["hard_limit"]
            elif op == "set_max_walking":
                constraints["max_walking_meters_per_day"] = operation["meters_per_day"]
            elif op == "add_required_place":
                self._append_unique_name(
                    constraints["required_place_names"],
                    str(operation["place_name"]),
                )
            elif op == "add_excluded_place":
                self._append_unique_name(
                    constraints["excluded_place_names"],
                    str(operation["place_name"]),
                )
            else:
                raise ApplicationError(
                    code="OPERATION_NOT_SUPPORTED",
                    message="阶段 4 不支持该反馈操作",
                    status_code=422,
                    details=[{"op": op}],
                )

        try:
            return TripRequest.model_validate(data)
        except ValidationError as exc:
            raise ApplicationError(
                code="VALIDATION_ERROR",
                message="反馈操作产生了无效旅行约束",
                status_code=422,
                details=[
                    {
                        "field": ".".join(str(part) for part in item["loc"]),
                        "reason": item["type"],
                    }
                    for item in exc.errors()
                ],
            ) from exc

    @staticmethod
    def _append_unique_name(values: list[str], new_value: str) -> None:
        known = {item.casefold() for item in values}
        if new_value.casefold() not in known:
            values.append(new_value)

    def _execute_plan(
        self,
        *,
        trip: TripRecord,
        run_id: UUID,
        trigger: PlanningRunTrigger,
        feedback_id: UUID | None,
        max_repair_attempts: int,
    ) -> PlanningRunRecord:
        if trip.active_planning_run_id is not None:
            raise ApplicationError(
                code="PLANNING_ALREADY_RUNNING",
                message="该旅行已有活动中的规划任务",
                status_code=409,
                retryable=True,
            )

        now = self._clock.now()
        run = PlanningRunRecord(
            id=run_id,
            trip_id=trip.id,
            trigger=trigger,
            status=PlanningRunStatus.PLANNING,
            progress_percent=10,
            current_step="build_facts",
            base_plan_version=trip.current_plan_version,
            result_plan_version=None,
            feedback_id=feedback_id,
            repair_attempts=0,
            max_repair_attempts=max_repair_attempts,
            error=None,
            created_at=now,
            started_at=now,
            finished_at=None,
        )
        self._repository.add_run(run)
        self._event(
            run_id=run.id,
            event_type=PlanningEventType.RUN_STARTED,
            step="build_facts",
            message="规划运行已开始",
        )

        active_trip = trip.model_copy(
            update={
                "status": (
                    TripStatus.REPLANNING
                    if trip.current_plan_version is not None
                    else TripStatus.PLANNING
                ),
                "active_planning_run_id": run.id,
                "revision": trip.revision + 1,
                "updated_at": now,
            }
        )
        self._repository.save_trip(active_trip)

        try:
            facts = self._facts_factory.build(
                request=active_trip.request,
                planned_at=now,
            )
            outcome = DeterministicPlanner(
                PlannerConfig(max_repair_rounds=max_repair_attempts)
            ).plan(facts)
        except ApplicationError as exc:
            self._fail_run(run=run, trip=active_trip, error=exc)
            raise

        if outcome.status != PlanningStatus.FEASIBLE:
            error = ApplicationError(
                code="NO_FEASIBLE_PLAN",
                message="当前约束组合无法生成可行计划",
                status_code=409,
                details=[
                    {
                        "violations": [
                            item.model_dump(mode="json")
                            for item in outcome.report.violations
                            if item.severity == "error"
                        ]
                    }
                ],
            )
            self._fail_run(run=run, trip=active_trip, error=error)
            raise error

        itinerary_data = outcome.itinerary.model_dump(mode="python")
        itinerary_data["trip_id"] = active_trip.id
        itinerary = Itinerary.model_validate(itinerary_data)

        previous_plans = self._repository.list_plans(active_trip.id)
        parent_version = previous_plans[-1].version if previous_plans else None
        version = 1 if parent_version is None else parent_version + 1

        if previous_plans:
            self._repository.save_plan(
                previous_plans[-1].model_copy(
                    update={"status": PlanStatus.SUPERSEDED}
                )
            )

        plan = PlanVersionRecord(
            id=uuid4(),
            trip_id=active_trip.id,
            version=version,
            parent_version=parent_version,
            status=PlanStatus.VALID,
            itinerary=itinerary,
            constraint_report=outcome.report,
            change_summary=(
                "根据用户反馈生成新版本"
                if trigger == PlanningRunTrigger.FEEDBACK
                else "生成初始旅行计划"
            ),
            trigger=(
                PlanTrigger.USER_FEEDBACK
                if trigger == PlanningRunTrigger.FEEDBACK
                else PlanTrigger.INITIAL
            ),
            planning_run_id=run.id,
            created_at=now,
            accepted_at=None,
        )
        self._repository.add_plan(plan)

        completed_run = run.model_copy(
            update={
                "status": PlanningRunStatus.COMPLETED,
                "progress_percent": 100,
                "current_step": None,
                "result_plan_version": version,
                "repair_attempts": max(0, outcome.attempts - 1),
                "finished_at": now,
            }
        )
        self._repository.save_run(completed_run)
        self._repository.save_trip(
            active_trip.model_copy(
                update={
                    "status": TripStatus.NEEDS_REVIEW,
                    "current_plan_version": version,
                    "active_planning_run_id": None,
                    "revision": active_trip.revision + 1,
                    "updated_at": now,
                }
            )
        )

        for violation in outcome.report.violations:
            self._event(
                run_id=run.id,
                event_type=PlanningEventType.CONSTRAINT_FOUND,
                step="validate",
                message=violation.message,
                payload={
                    "code": violation.code.value,
                    "severity": violation.severity.value,
                },
            )
        if outcome.repair_notes:
            self._event(
                run_id=run.id,
                event_type=PlanningEventType.REPAIR_STARTED,
                step="repair",
                message="规划器执行了有限修正",
                payload={"notes": list(outcome.repair_notes)},
            )
        self._event(
            run_id=run.id,
            event_type=PlanningEventType.PLAN_CREATED,
            step="persist_plan",
            message=f"已生成计划版本 {version}",
            payload={"plan_version": version},
        )
        self._event(
            run_id=run.id,
            event_type=PlanningEventType.REVIEW_REQUIRED,
            step="review",
            message="计划等待用户确认",
        )
        self._event(
            run_id=run.id,
            event_type=PlanningEventType.RUN_COMPLETED,
            step=None,
            message="规划运行已完成",
        )
        return completed_run

    def _fail_run(
        self,
        *,
        run: PlanningRunRecord,
        trip: TripRecord,
        error: ApplicationError,
    ) -> None:
        now = self._clock.now()
        self._repository.save_run(
            run.model_copy(
                update={
                    "status": PlanningRunStatus.FAILED,
                    "current_step": None,
                    "error": {
                        "code": error.code,
                        "message": error.message,
                        "retryable": error.retryable,
                    },
                    "finished_at": now,
                }
            )
        )
        self._repository.save_trip(
            trip.model_copy(
                update={
                    "status": TripStatus.FAILED,
                    "active_planning_run_id": None,
                    "revision": trip.revision + 1,
                    "updated_at": now,
                }
            )
        )
        self._event(
            run_id=run.id,
            event_type=PlanningEventType.RUN_FAILED,
            step=None,
            message=error.message,
            payload={"code": error.code},
        )

    def _event(
        self,
        *,
        run_id: UUID,
        event_type: PlanningEventType,
        step: str | None,
        message: str,
        payload: dict[str, object] | None = None,
    ) -> None:
        sequence = len(self._repository.list_events(run_id)) + 1
        self._repository.add_event(
            PlanningEventRecord(
                id=str(sequence),
                run_id=run_id,
                sequence=sequence,
                type=event_type,
                step=step,
                message=message,
                payload=payload or {},
                created_at=self._clock.now(),
            )
        )
~~~

### 为什么 Service 这么长

它实现的是完整用例，而不是算法函数：创建运行、更新状态、构造事实、调用规划器、处理无解、保存版本、写事件并清理 active run。路由如果承担这些步骤，会很难测试，也无法在以后改成队列消费。

### 一个必须注意的 ID 问题

阶段 3 的 stable_trip_id 根据 TripRequest 生成；阶段 4 已经拥有真正的 REST Trip.id。应用层必须把生成结果映射到资源 ID，并通过 Itinerary.model_validate 重新校验。

不要把未经重新验证的 model_copy(update={"trip_id": ...}) 当成最终计划。
+---

## 12. API 映射器

在文件清单中增加 backend/app/api/mappers.py。创建它：

~~~python
from app.api.schemas import (
    FeedbackRecordResponse,
    FeedbackScope,
    PlanListResponse,
    PlanVersionResponse,
    PlanVersionSummary,
    PlanningEventResponse,
    PlanningRunResponse,
    TripResponse,
)
from app.application.models import (
    FeedbackRecord,
    PlanningEventRecord,
    PlanningRunRecord,
    PlanVersionRecord,
    TripRecord,
)


def to_trip_response(record: TripRecord) -> TripResponse:
    request = record.request
    return TripResponse(
        id=record.id,
        status=record.status,
        revision=record.revision,
        origin=request.origin,
        destination=request.destination,
        destination_timezone=request.destination_timezone,
        date_range=request.date_range,
        travelers=request.travelers,
        preferences=request.preferences,
        constraints=request.constraints,
        locale=request.locale,
        display_currency=request.display_currency,
        notes=request.notes,
        current_plan_version=record.current_plan_version,
        active_planning_run_id=record.active_planning_run_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def to_run_response(record: PlanningRunRecord) -> PlanningRunResponse:
    return PlanningRunResponse.model_validate(record.model_dump(mode="python"))


def to_plan_response(record: PlanVersionRecord) -> PlanVersionResponse:
    return PlanVersionResponse.model_validate(record.model_dump(mode="python"))


def to_plan_summary(record: PlanVersionRecord) -> PlanVersionSummary:
    violations = record.constraint_report.violations
    return PlanVersionSummary(
        id=record.id,
        trip_id=record.trip_id,
        version=record.version,
        parent_version=record.parent_version,
        status=record.status,
        day_count=len(record.itinerary.days),
        planned_total=record.itinerary.budget.planned_total,
        error_count=sum(item.severity == "error" for item in violations),
        warning_count=sum(item.severity == "warning" for item in violations),
        change_summary=record.change_summary,
        trigger=record.trigger,
        planning_run_id=record.planning_run_id,
        created_at=record.created_at,
    )


def to_plan_list(records: list[PlanVersionRecord]) -> PlanListResponse:
    return PlanListResponse(items=[to_plan_summary(item) for item in records])


def to_event_response(record: PlanningEventRecord) -> PlanningEventResponse:
    return PlanningEventResponse.model_validate(record.model_dump(mode="python"))


def to_feedback_response(record: FeedbackRecord) -> FeedbackRecordResponse:
    return FeedbackRecordResponse.model_validate(
        {
            "id": record.id,
            "trip_id": record.trip_id,
            "base_plan_version": record.base_plan_version,
            "message": record.message,
            "operations": record.operations,
            "scope": {
                "dates": record.affected_dates,
                "activity_ids": record.affected_activity_ids,
                "global": record.global_scope,
            },
            "requires_clarification": record.requires_clarification,
            "clarification_question": record.clarification_question,
            "planning_run_id": record.planning_run_id,
            "created_at": record.created_at,
        }
    )
~~~

为什么需要 Mapper：

- Repository 返回应用记录；
- 路由承诺 API Response；
- Mapper 是两者之间唯一的字段翻译位置；
- 以后内部记录改变，不必修改每一个路由。

---

## 13. 依赖装配

创建 backend/app/api/dependencies.py：

~~~python
from fastapi import Request

from app.application.service import TravelService


def get_travel_service(request: Request) -> TravelService:
    """从 app.state 取得当前应用实例绑定的 Service。"""
    return request.app.state.travel_service
~~~

测试会给 create_app 传入使用 FixedClock 的 Service；生产环境使用 SystemClock。不要在路由模块顶层创建全局 Repository，否则测试之间会相互污染。

---

## 14. 旅行路由

创建 backend/app/api/routes/trips.py：

~~~python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_travel_service
from app.api.mappers import to_trip_response
from app.api.schemas import TripCreateRequest, TripResponse
from app.application.service import TravelService

router = APIRouter(prefix="/trips", tags=["trips"])
Service = Annotated[TravelService, Depends(get_travel_service)]


@router.post(
    "",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_trip",
    summary="创建旅行",
)
def create_trip(
    payload: TripCreateRequest,
    response: Response,
    service: Service,
) -> TripResponse:
    trip = service.create_trip(payload)
    response.headers["Location"] = f"/api/v1/trips/{trip.id}"
    response.headers["ETag"] = f'"{trip.revision}"'
    return to_trip_response(trip)


@router.get(
    "/{trip_id}",
    response_model=TripResponse,
    operation_id="get_trip",
    summary="获取旅行",
)
def get_trip(
    trip_id: UUID,
    response: Response,
    service: Service,
) -> TripResponse:
    trip = service.get_trip(trip_id)
    response.headers["ETag"] = f'"{trip.revision}"'
    return to_trip_response(trip)
~~~

路由只完成四件事：

1. FastAPI 校验输入；
2. 调用 Service；
3. 设置 HTTP Header；
4. 使用 Mapper 返回 DTO。

---

## 15. 规划运行与事件路由

创建 backend/app/api/routes/planning.py：

~~~python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_travel_service
from app.api.mappers import to_event_response, to_run_response
from app.api.schemas import (
    PlanningEventListResponse,
    PlanningRunResponse,
    StartPlanningRequest,
    StartPlanningResponse,
)
from app.application.service import TravelService

router = APIRouter(prefix="/trips/{trip_id}/planning-runs", tags=["planning"])
Service = Annotated[TravelService, Depends(get_travel_service)]


@router.post(
    "",
    response_model=StartPlanningResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="start_planning_run",
    summary="启动规划运行",
)
def start_planning_run(
    trip_id: UUID,
    payload: StartPlanningRequest,
    service: Service,
) -> StartPlanningResponse:
    # force_refresh_tools 在固定事实阶段没有作用，但保留在契约中。
    run = service.start_planning(
        trip_id=trip_id,
        max_repair_attempts=payload.max_repair_attempts,
    )
    return StartPlanningResponse(
        planning_run=to_run_response(run),
        events_url=f"/api/v1/trips/{trip_id}/planning-runs/{run.id}/events",
    )


@router.get(
    "/{run_id}",
    response_model=PlanningRunResponse,
    operation_id="get_planning_run",
    summary="获取规划运行",
)
def get_planning_run(
    trip_id: UUID,
    run_id: UUID,
    service: Service,
) -> PlanningRunResponse:
    return to_run_response(service.get_run(trip_id, run_id))


@router.get(
    "/{run_id}/events",
    response_model=PlanningEventListResponse,
    operation_id="list_planning_events",
    summary="获取公开规划事件",
)
def list_planning_events(
    trip_id: UUID,
    run_id: UUID,
    service: Service,
) -> PlanningEventListResponse:
    return PlanningEventListResponse(
        items=[
            to_event_response(item)
            for item in service.list_events(trip_id, run_id)
        ]
    )
~~~

### 为什么 events 现在返回 JSON，不直接做 SSE

阶段 4 内部规划同步完成，JSON 事件列表最容易验证事件是否正确、是否泄漏隐藏推理。最终 api-contract 要求同一路径升级为 text/event-stream，并支持 Last-Event-ID。升级时 Event 对象和事件存储可以复用。

事件 payload 只能包含公开进度、规则码、计数和资源 ID；不能放模型思维链、密钥或第三方原始响应。

---

## 16. 计划路由

创建 backend/app/api/routes/plans.py：

~~~python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_travel_service
from app.api.mappers import to_plan_list, to_plan_response
from app.api.schemas import PlanListResponse, PlanVersionResponse
from app.application.service import TravelService

router = APIRouter(prefix="/trips/{trip_id}/plans", tags=["plans"])
Service = Annotated[TravelService, Depends(get_travel_service)]


@router.get(
    "",
    response_model=PlanListResponse,
    operation_id="list_plan_versions",
    summary="获取计划版本列表",
)
def list_plan_versions(
    trip_id: UUID,
    service: Service,
) -> PlanListResponse:
    return to_plan_list(service.list_plans(trip_id))


@router.get(
    "/{version}",
    response_model=PlanVersionResponse,
    operation_id="get_plan_version",
    summary="获取完整计划版本",
)
def get_plan_version(
    trip_id: UUID,
    version: str,
    service: Service,
) -> PlanVersionResponse:
    return to_plan_response(service.get_plan(trip_id, version))
~~~

列表只返回摘要，不重复返回多份完整 Itinerary。查看某个版本时才获取完整对象。

---

## 17. 反馈路由

创建 backend/app/api/routes/feedback.py：

~~~python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_travel_service
from app.api.mappers import to_feedback_response, to_run_response
from app.api.schemas import FeedbackCreateRequest, FeedbackResponse
from app.application.service import TravelService

router = APIRouter(prefix="/trips/{trip_id}/feedback", tags=["feedback"])
Service = Annotated[TravelService, Depends(get_travel_service)]


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="create_feedback",
    summary="提交反馈并按需重规划",
)
def create_feedback(
    trip_id: UUID,
    payload: FeedbackCreateRequest,
    response: Response,
    service: Service,
) -> FeedbackResponse:
    feedback, run = service.submit_feedback(
        trip_id=trip_id,
        base_plan_version=payload.base_plan_version,
        message=payload.message,
        operations=[
            item.model_dump(mode="python")
            for item in payload.client_operations
        ],
        auto_start_replanning=payload.auto_start_replanning,
    )

    if feedback.requires_clarification:
        response.status_code = status.HTTP_200_OK

    return FeedbackResponse(
        feedback=to_feedback_response(feedback),
        planning_run=None if run is None else to_run_response(run),
        events_url=(
            None
            if run is None
            else f"/api/v1/trips/{trip_id}/planning-runs/{run.id}/events"
        ),
    )
~~~

两种响应：

- 操作明确且自动重规划：202；
- 没有结构化操作，需要用户澄清：200。

---

## 18. 聚合 API Router

创建 backend/app/api/router.py：

~~~python
from fastapi import APIRouter

from app.api.routes.feedback import router as feedback_router
from app.api.routes.planning import router as planning_router
from app.api.routes.plans import router as plans_router
from app.api.routes.trips import router as trips_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(trips_router)
api_router.include_router(planning_router)
api_router.include_router(plans_router)
api_router.include_router(feedback_router)
~~~

为新建目录补充空的 __init__.py：

~~~text
backend/app/application/__init__.py
backend/app/infrastructure/__init__.py
backend/app/api/__init__.py
backend/app/api/routes/__init__.py
~~~

---

## 19. 修改 FastAPI 应用工厂

修改 backend/app/main.py：

~~~python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import install_error_handlers
from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.application.clock import SystemClock
from app.application.facts import FixturePlanningFactsFactory
from app.application.service import TravelService
from app.core.config import get_settings
from app.infrastructure.memory_repository import InMemoryTravelRepository


def build_default_service() -> TravelService:
    return TravelService(
        repository=InMemoryTravelRepository(),
        clock=SystemClock(),
        facts_factory=FixturePlanningFactsFactory(),
    )


def create_app(service: TravelService | None = None) -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="TravelMind dynamic travel planning agent API",
        lifespan=lifespan,
    )
    application.state.travel_service = service or build_default_service()

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.middleware("http")
    async def attach_request_id(request: Request, call_next):
        request.state.request_id = request.headers.get(
            "X-Request-ID",
            str(uuid4()),
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    install_error_handlers(application)
    application.include_router(health_router)
    application.include_router(api_router)
    return application


app = create_app()
~~~

为什么 create_app 接受 Service：

- 生产使用默认内存仓库和系统时钟；
- 测试传入全新仓库和固定时钟；
- 测试之间不会共享状态；
- 不需要 monkeypatch 模块全局变量。

代码中的 lifespan 当前为空，是为下一阶段数据库连接池和任务资源预留的标准位置。

---

## 20. OpenAPI 错误 Schema

为了让非 2xx 响应也有命名 Schema，在 schemas.py 末尾增加：

~~~python
class ApiErrorInfo(ApiModel):
    code: str
    message: str
    details: list[dict[str, object]]
    request_id: str
    retryable: bool


class ApiErrorResponse(ApiModel):
    error: ApiErrorInfo
~~~

然后为路由装饰器增加对应 responses。例如：

~~~python
@router.get(
    "/{trip_id}",
    response_model=TripResponse,
    operation_id="get_trip",
    responses={
        404: {
            "model": ApiErrorResponse,
            "description": "旅行不存在",
        }
    },
)
def get_trip(trip_id: UUID) -> TripResponse:
    ...
~~~

至少要声明实际可能出现的主要分支：

| 接口 | 错误 |
| --- | --- |
| 创建旅行 | 422 VALIDATION_ERROR |
| 获取旅行 | 404 TRIP_NOT_FOUND |
| 启动规划 | 404、409 PLANNING_ALREADY_RUNNING、409 NO_FEASIBLE_PLAN、502 TOOL_DATA_INCOMPLETE |
| 获取计划 | 404 PLAN_NOT_FOUND |
| 提交反馈 | 404、409 VERSION_CONFLICT、422 VALIDATION_ERROR |

不要为了让 Swagger 好看而声明代码永远不会返回的错误，也不能遗漏已经实现的重要错误。
+---

## 21. API 测试公共夹具

创建 backend/tests/api/__init__.py 空文件。

创建 backend/tests/api/conftest.py：

~~~python
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.application.clock import FixedClock
from app.application.facts import FixturePlanningFactsFactory
from app.application.service import TravelService
from app.fixtures.loader import load_tokyo_trip_request
from app.infrastructure.memory_repository import InMemoryTravelRepository
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    service = TravelService(
        repository=InMemoryTravelRepository(),
        clock=FixedClock(datetime(2026, 9, 30, tzinfo=UTC)),
        facts_factory=FixturePlanningFactsFactory(),
    )
    return TestClient(create_app(service))


@pytest.fixture
def tokyo_payload() -> dict[str, object]:
    return load_tokyo_trip_request().model_dump(mode="json")


@pytest.fixture
def created_trip(
    client: TestClient,
    tokyo_payload: dict[str, object],
) -> dict[str, object]:
    response = client.post("/api/v1/trips", json=tokyo_payload)
    assert response.status_code == 201
    return response.json()
~~~

每个测试获得全新的内存仓库；固定时钟保证生成时间和约束报告完全可重复。

---

## 22. 创建、规划和查询测试

创建 backend/tests/api/test_trip_planning_flow.py：

~~~python
from fastapi.testclient import TestClient


def test_create_plan_and_read_current_version(
    client: TestClient,
    created_trip: dict[str, object],
) -> None:
    trip_id = created_trip["id"]

    planning_response = client.post(
        f"/api/v1/trips/{trip_id}/planning-runs",
        json={
            "mode": "initial",
            "force_refresh_tools": False,
            "max_repair_attempts": 3,
        },
    )

    assert planning_response.status_code == 202
    run = planning_response.json()["planning_run"]
    assert run["status"] == "completed"
    assert run["result_plan_version"] == 1

    plan_response = client.get(
        f"/api/v1/trips/{trip_id}/plans/current"
    )
    assert plan_response.status_code == 200
    plan = plan_response.json()
    assert plan["version"] == 1
    assert plan["status"] == "valid"
    assert plan["itinerary"]["trip_id"] == trip_id
    assert plan["constraint_report"]["passed"] is True

    trip_response = client.get(f"/api/v1/trips/{trip_id}")
    assert trip_response.status_code == 200
    assert trip_response.json()["status"] == "needs_review"
    assert trip_response.json()["current_plan_version"] == 1
    assert trip_response.headers["etag"] == '"3"'


def test_plan_list_returns_summary_not_complete_days(
    client: TestClient,
    created_trip: dict[str, object],
) -> None:
    trip_id = created_trip["id"]
    client.post(
        f"/api/v1/trips/{trip_id}/planning-runs",
        json={},
    )

    response = client.get(f"/api/v1/trips/{trip_id}/plans")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["version"] == 1
    assert item["day_count"] == 5
    assert "itinerary" not in item


def test_planning_events_are_public_and_ordered(
    client: TestClient,
    created_trip: dict[str, object],
) -> None:
    trip_id = created_trip["id"]
    body = client.post(
        f"/api/v1/trips/{trip_id}/planning-runs",
        json={},
    ).json()

    response = client.get(body["events_url"])

    assert response.status_code == 200
    events = response.json()["items"]
    assert [item["sequence"] for item in events] == list(
        range(1, len(events) + 1)
    )
    assert events[0]["type"] == "run_started"
    assert events[-1]["type"] == "run_completed"
    assert all("chain_of_thought" not in item["payload"] for item in events)
~~~

为什么 ETag 是 3：

1. 创建时 revision=1；
2. 开始规划时改为 planning，revision=2；
3. 完成时改为 needs_review，revision=3。

测试不要只断言 200，还应断言资源状态迁移。

---

## 23. 反馈和版本测试

创建 backend/tests/api/test_feedback_flow.py：

~~~python
from fastapi.testclient import TestClient


def create_first_plan(
    client: TestClient,
    trip_id: str,
) -> None:
    response = client.post(
        f"/api/v1/trips/{trip_id}/planning-runs",
        json={},
    )
    assert response.status_code == 202


def test_structured_feedback_creates_second_plan_version(
    client: TestClient,
    created_trip: dict[str, object],
) -> None:
    trip_id = created_trip["id"]
    create_first_plan(client, trip_id)

    response = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json={
            "base_plan_version": 1,
            "message": "每天最多走 1 公里",
            "client_operations": [
                {
                    "op": "set_max_walking",
                    "meters_per_day": 1000,
                    "reason": "用户希望减少步行",
                }
            ],
            "auto_start_replanning": True,
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["feedback"]["requires_clarification"] is False
    assert body["planning_run"]["status"] == "completed"
    assert body["planning_run"]["result_plan_version"] == 2

    versions = client.get(
        f"/api/v1/trips/{trip_id}/plans"
    ).json()["items"]
    assert [item["version"] for item in versions] == [1, 2]
    assert versions[0]["status"] == "superseded"
    assert versions[1]["status"] == "valid"

    current = client.get(
        f"/api/v1/trips/{trip_id}/plans/current"
    ).json()
    assert current["version"] == 2
    assert all(
        day["statistics"]["walking_meters"] <= 1000
        for day in current["itinerary"]["days"]
    )


def test_message_without_operations_requires_clarification(
    client: TestClient,
    created_trip: dict[str, object],
) -> None:
    trip_id = created_trip["id"]
    create_first_plan(client, trip_id)

    response = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json={
            "base_plan_version": 1,
            "message": "第二天轻松一点",
            "client_operations": [],
            "auto_start_replanning": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["feedback"]["requires_clarification"] is True
    assert body["feedback"]["clarification_question"]
    assert body["planning_run"] is None
    assert body["events_url"] is None


def test_feedback_rejects_stale_base_version(
    client: TestClient,
    created_trip: dict[str, object],
) -> None:
    trip_id = created_trip["id"]
    create_first_plan(client, trip_id)

    response = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json={
            "base_plan_version": 999,
            "message": "减少步行",
            "client_operations": [
                {
                    "op": "set_max_walking",
                    "meters_per_day": 1000,
                }
            ],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VERSION_CONFLICT"
~~~

这个测试证明计划不是原地覆盖：

~~~text
版本 1：superseded，仍可查询
版本 2：valid，成为 current
~~~

---

## 24. 错误响应测试

创建 backend/tests/api/test_errors.py：

~~~python
from uuid import uuid4

from fastapi.testclient import TestClient


def test_missing_trip_returns_stable_error(client: TestClient) -> None:
    response = client.get(f"/api/v1/trips/{uuid4()}")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "TRIP_NOT_FOUND"
    assert error["retryable"] is False
    assert error["request_id"]


def test_invalid_request_uses_common_error_shape(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/trips",
        json={"destination": "东京"},
        headers={"X-Request-ID": "test-request-001"},
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["request_id"] == "test-request-001"
    assert error["details"]
    assert response.headers["x-request-id"] == "test-request-001"


def test_fixture_scope_error_is_explicit(
    client: TestClient,
    tokyo_payload: dict[str, object],
) -> None:
    tokyo_payload["destination"] = "大阪"
    created = client.post("/api/v1/trips", json=tokyo_payload).json()

    response = client.post(
        f"/api/v1/trips/{created['id']}/planning-runs",
        json={},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "TOOL_DATA_INCOMPLETE"
~~~

第三方/事实不足不能伪装成空计划，也不能把 Python 异常栈返回给客户端。

---

## 25. OpenAPI 契约测试

创建 backend/tests/api/test_openapi.py：

~~~python
from fastapi.testclient import TestClient


def test_openapi_has_unique_operation_ids(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    operation_ids = [
        operation["operationId"]
        for path_item in schema["paths"].values()
        for method, operation in path_item.items()
        if method.lower() in {
            "get",
            "post",
            "put",
            "patch",
            "delete",
        }
    ]

    assert len(operation_ids) == len(set(operation_ids))


def test_openapi_exposes_named_contracts(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    component_names = set(schema["components"]["schemas"])

    assert {
        "TripCreateRequest",
        "TripResponse",
        "PlanningRunResponse",
        "PlanVersionResponse",
        "FeedbackCreateRequest",
        "ApiErrorResponse",
    } <= component_names

    assert "/api/v1/trips" in schema["paths"]
    assert "/api/v1/trips/{trip_id}/planning-runs" in schema["paths"]
    assert "/api/v1/trips/{trip_id}/plans/{version}" in schema["paths"]
~~~

OpenAPI 是前端类型的权威来源。operation_id 重复会导致生成的客户端函数重名，因此必须测试。

---

## 26. 运行顺序

先只运行阶段 4：

~~~powershell
cd backend
uv run pytest -q tests/api
uv run ruff check app tests
uv run ruff format --check app tests
~~~

再运行完整后端回归：

~~~powershell
uv run pytest -q
uv lock --check
uv run python -m compileall -q app tests
~~~

启动 API：

~~~powershell
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
~~~

检查：

~~~text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/openapi.json
http://127.0.0.1:8000/health/live
~~~

最后执行前端回归：

~~~powershell
cd ../frontend
pnpm lint
pnpm build
~~~

---

## 27. 前端从 OpenAPI 生成类型

不要在 frontend 手写另一份 TripResponse 或 PlanVersion。

安装生成工具：

~~~powershell
cd frontend
pnpm add -D openapi-typescript
~~~

在 frontend/package.json 的 scripts 中增加：

~~~json
{
  "api:generate": "openapi-typescript http://127.0.0.1:8000/openapi.json -o src/lib/api/schema.d.ts"
}
~~~

启动后端后运行：

~~~powershell
pnpm api:generate
~~~

手写的 frontend/src/lib/api/client.ts 只负责发送请求：

~~~typescript
import type { paths } from "./schema";

type CreateTripBody =
  paths["/api/v1/trips"]["post"]["requestBody"]["content"]["application/json"];

type CreateTripResponse =
  paths["/api/v1/trips"]["post"]["responses"]["201"]["content"]["application/json"];

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function createTrip(
  body: CreateTripBody,
): Promise<CreateTripResponse> {
  const response = await fetch(`${API_BASE}/api/v1/trips`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw await response.json();
  }
  return response.json() as Promise<CreateTripResponse>;
}
~~~

这里的反引号是 TypeScript 模板字符串。生成文件应提交到仓库，让前端构建不依赖后端正在运行；但 CI 要重新生成并检查是否出现未提交差异。

---

## 28. 阶段 4 验收清单

### 28.1 架构

- [ ] domain、constraints 和 planning 不导入 FastAPI。
- [ ] 路由不直接访问内存字典或调用 DeterministicPlanner。
- [ ] Application Service 不依赖 Request、Response 或 HTTPException。
- [ ] Service 只依赖 TravelRepository 协议。
- [ ] 创建请求和服务端响应使用不同 DTO。
- [ ] 固定事实适配集中在 Facts Factory。

### 28.2 REST 契约

- [ ] 路径以 /api/v1 为前缀。
- [ ] 每个接口有稳定且唯一的 operation_id。
- [ ] 创建返回 201、Location、ETag。
- [ ] 启动规划返回 202 和 PlanningRun。
- [ ] 资源不存在返回稳定 404 code。
- [ ] 输入不合法统一返回 ApiError。
- [ ] X-Request-ID 可以透传并回写。
- [ ] 计划列表不返回完整 days。
- [ ] current 能解析到当前版本。

### 28.3 状态和版本

- [ ] Trip revision 随状态改变递增。
- [ ] 规划期间设置 active_planning_run_id。
- [ ] 成功后清除 active run，并进入 needs_review。
- [ ] 初次规划产生版本 1。
- [ ] 反馈基于旧版本时返回 VERSION_CONFLICT。
- [ ] 重规划产生新版本，不覆盖旧 Itinerary。
- [ ] 旧版本标记 superseded，仍可按版本查询。
- [ ] Itinerary.trip_id 等于 REST Trip.id。

### 28.4 规划和反馈

- [ ] API 真实调用阶段 3 DeterministicPlanner。
- [ ] 每个候选计划经过阶段 2 约束引擎。
- [ ] 无解返回 NO_FEASIBLE_PLAN 和结构化 violations。
- [ ] 没有结构化操作时要求澄清，不解析自然语言。
- [ ] 反馈操作重新通过 TripRequest 完整校验。
- [ ] 预算或步行反馈能生成第二个可行版本。
- [ ] 事件连续编号，只含公开信息。

### 28.5 工程质量

- [ ] tests/api 全部通过。
- [ ] 完整后端测试通过。
- [ ] Ruff 检查和格式检查通过。
- [ ] uv 锁文件检查和 compileall 通过。
- [ ] Swagger UI 能完成创建、规划和查询。
- [ ] OpenAPI operation_id 无重复。
- [ ] 前端 lint 和生产构建通过。
- [ ] 前端类型来自 OpenAPI，而不是手写复制。

---

## 29. 当前示例与最终 api-contract 的差异

为了严格控制阶段范围，本文主线没有一次实现 api-contract 中的所有接口：

| 最终能力 | 本教程状态 | 后续处理 |
| --- | --- | --- |
| PATCH/DELETE/旅行列表 | 未实现 | REST 资源管理扩展 |
| Idempotency-Key | 未实现 | 加幂等记录表或缓存 |
| If-Match 修改 | 未实现 | PATCH 与接受计划时加入 |
| 计划 diff/validate/accept | 未实现 | 计划评审阶段 |
| 全部 FeedbackOperation | 仅四种请求级操作 | Agent 与动态重规划阶段 |
| 真正异步任务 | 内部同步、外部任务模型 | 队列/后台任务 |
| SSE 与 Last-Event-ID | 暂用 JSON 事件列表 | SSE 阶段 |
| 数据库事务 | 内存 Repository | 持久化阶段 |
| 真实 Provider | 东京固定事实 | 工具集成阶段 |

这不是让实现和契约永久分叉，而是把当前垂直切片写清楚。每增加一项能力，都应先更新命名 Schema 和测试，再实现路由。

如果你的阶段 4 验收定义要求完整覆盖 api-contract，而不只是详细计划中的首批纵向流程，应继续实现表中前三项后再标记完成。

---

## 30. 常见错误

### 30.1 路由里直接写规划算法

结果是 TestClient 测试只能走 HTTP，后台任务无法复用。算法留在 planning，用例编排留在 application。

### 30.2 直接把 TripRequest 当成旅行资源

TripRequest 没有 id、status、revision 和版本关系。它只是需求快照，不是 REST 聚合资源。

### 30.3 覆盖同一份 Itinerary

覆盖会让反馈前后无法比较，也无法解释用户的修改历史。每次成功规划必须创建新的 PlanVersion。

### 30.4 使用 model_copy 绕过最终校验

model_copy(update=...) 默认不会重新验证更新字段。跨边界生成最终 Itinerary 或应用反馈后，必须调用 model_validate。

### 30.5 内部同步就返回 200 Itinerary

这会把客户端绑定到同步实现。阶段 4 仍返回 202 PlanningRun，未来异步化不用修改主契约。

### 30.6 把异常字符串原样发给前端

第三方异常、文件路径和堆栈可能泄漏实现细节。ApplicationError 映射为稳定 ApiError，未分类异常只在服务端日志记录。

### 30.7 事件中放隐藏推理

事件只告诉用户“正在做什么”和“得到什么公开结果”，不能输出模型思维链。后续使用 LLM 时也必须遵守这一点。

---

## 31. 学习检查题

完成代码后，应能回答：

1. API DTO、TripRequest 和 TripRecord 分别负责什么？
2. 为什么 Application Service 不能抛 HTTPException？
3. 为什么内存 Repository 也要返回 deep copy？
4. 为什么内部同步执行仍返回 PlanningRun？
5. 为什么阶段 3 生成的 trip_id 要映射成 REST Trip.id？
6. revision、PlanVersion.version 和 base_plan_version 有什么区别？
7. 为什么没有 client_operations 时不能用关键词猜测反馈？
8. 为什么旧计划要保留，而不是原地覆盖？
9. JSON 事件列表升级 SSE 时，哪些对象可以原样复用？
10. 将内存仓库换成数据库时，哪些层不应该修改？

能独立解释并通过验收清单，才说明真正掌握了阶段 4 的应用边界和 REST 设计。
