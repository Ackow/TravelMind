from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass(slots=True)
class LLMUsage:
    """单次调用的 Token 与耗时统计。"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int


@dataclass(slots=True)
class LLMResponse[T]:
    """带有统计元数据的强类型结构化响应。"""
    data: T
    usage: LLMUsage
    raw_content: str
    model: str


class LLMClient(Protocol):
    """LLM 结构化输出客户端协议。"""

    def generate_structured(
        self,
        *,
        schema: type[T],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_retries: int = 2,
    ) -> LLMResponse[T]:
        """输入 Prompt 并强制输出校验通过的 Pydantic 模型实例。"""
        ...


class FakeLLMClient:
    """供单元测试使用的可编程 Fake LLM 客户端。"""

    def __init__(self, canned_responses: Sequence[BaseModel] | None = None) -> None:
        self._queue: list[BaseModel] = list(canned_responses or [])
        self.call_history: list[dict[str, Any]] = []

    def set_response(self, response: BaseModel) -> None:
        self._queue = [response]

    def add_response(self, response: BaseModel) -> None:
        self._queue.append(response)

    def generate_structured(
        self,
        *,
        schema: type[T],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_retries: int = 2,
    ) -> LLMResponse[T]:
        self.call_history.append({
            "schema": schema,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "temperature": temperature,
        })
        if not self._queue:
            raise RuntimeError("FakeLLMClient queue is empty; no canned response provided.")
        canned = self._queue.pop(0)
        if not isinstance(canned, schema):
            # 尝试通过 model_dump / validate 转换
            canned = schema.model_validate(canned.model_dump())
        return LLMResponse(
            data=canned,
            usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150, latency_ms=12),
            raw_content=canned.model_dump_json(),
            model="fake-test-model",
        )