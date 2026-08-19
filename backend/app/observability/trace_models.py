from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PublicEventType(StrEnum):
    """公开安全的 Trace 事件类型"""

    RUN_STARTED = "run_started"  # 规划任务启动
    NODE_ENTER = "node_enter"  # 进入某个工作流节点
    NODE_EXIT = "node_exit"  # 节点处理完毕
    TOOL_CALLED = "tool_called"  # 调用外部事实工具
    CONSTRAINT_AUDITED = "constraint_audited"  # 规则引擎审计结果
    REPAIR_ATTEMPTED = "repair_attempted"  # 自愈修复尝试
    HUMAN_INTERRUPT = "human_interrupt"  # 挂起等待人工审阅
    DIFF_GENERATED = "diff_generated"  # 生成版本变更对比
    RUN_COMPLETED = "run_completed"  # 规划圆满达成
    RUN_FAILED = "run_failed"  # 规划失败


class PublicTraceEvent(BaseModel):
    """面向前端安全展示的 Trace 节点事件模型"""

    event_id: str = Field(description="事件唯一跟踪 ID")
    run_id: UUID = Field(description="所属规划 Run ID")
    trip_id: UUID = Field(description="所属旅行 ID")
    sequence: int = Field(description="严格单调递增序号")
    event_type: PublicEventType = Field(description="事件类型")
    stage_name: str = Field(description="所属流程阶段名称")
    message: str = Field(description="人类可读的实时进度摘要")
    metrics: dict[str, Any] = Field(
        default_factory=dict, description="耗时、数据条数、违规数等统计指标"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
