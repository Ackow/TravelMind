import time
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.agent.llm_client import LLMClient, LLMResponse, LLMUsage

T = TypeVar("T", bound=BaseModel)


class OpenAICompatibleLLMClient(LLMClient):
    """支持 OpenAI, DeepSeek, Moonshot, Qwen 等兼容接口的标准实现。"""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
    ) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def generate_structured(
        self, *, schema=type[T], system_prompt, user_prompt, temperature=0.1, max_retries=2
    ) -> LLMResponse[T]:
        start_time = time.perf_counter()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        import json

        last_err: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                try:
                    # 优先使用 OpenAI 官方 beta.chat.completions.parse 结构化输出
                    completion = self._client.beta.chat.completions.parse(
                        model=self._model,
                        messages=messages,
                        response_format=schema,
                        temperature=temperature,
                    )
                    parsed_data = completion.choices[0].message.parsed
                    raw_text = completion.choices[0].message.content or ""
                except Exception:
                    # 兼容非 OpenAI 官方原生代理平台（如 OpenCode Go / DeepSeek 等）
                    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
                    augmented_messages = [
                        {
                            "role": "system",
                            "content": f"{system_prompt}\n\nStrict requirement: Output ONLY valid JSON matching this schema:\n{schema_json}",
                        },
                        {"role": "user", "content": user_prompt},
                    ]
                    raw_resp = self._client.chat.completions.create(
                        model=self._model,
                        messages=augmented_messages,
                        response_format={"type": "json_object"},
                        temperature=temperature,
                    )
                    raw_text = raw_resp.choices[0].message.content or "{}"
                    parsed_data = schema.model_validate_json(raw_text)
                    completion = raw_resp

                latency = int((time.perf_counter() - start_time) * 1000)
                usage_raw = completion.usage
                usage = LLMUsage(
                    prompt_tokens=usage_raw.prompt_tokens if usage_raw else 0,
                    completion_tokens=usage_raw.completion_tokens if usage_raw else 0,
                    total_tokens=usage_raw.total_tokens if usage_raw else 0,
                    latency_ms=latency,
                )
                if parsed_data is None:
                    raise ValueError("Failed to parse structured model response")

                return LLMResponse(
                    data=parsed_data,
                    usage=usage,
                    raw_content=raw_text,
                    model=self._model,
                )

            except (ValidationError, ValueError, Exception) as exc:
                last_err = exc
                if attempt < max_retries:
                    # 将校验错误回喂给模型进行自愈修正
                    (messages.append({"role": "assistant", "content": str(exc)}),)
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Your last JSON response failed validation: {exc}. Please fix the structure.",
                        }
                    )

        raise RuntimeError(
            f"LLM structured output failed after {max_retries} retries"
        ) from last_err
