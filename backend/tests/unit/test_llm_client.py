from pydantic import BaseModel, Field

from app.agent.llm_client import FakeLLMClient


class DemoSchema(BaseModel):
    city: str
    rating: int = Field(ge=1, le=5)


def test_fake_llm_client_returns_typed_model() -> None:
    expected = DemoSchema(city="Tokyo", rating=5)
    client = FakeLLMClient([expected])

    response = client.generate_structured(
        schema=DemoSchema,
        system_prompt="You are a helper.",
        user_prompt="Recommend a city.",
    )

    assert response.data.city == "Tokyo"
    assert response.data.rating == 5
    assert response.usage.latency_ms > 0
    assert len(client.call_history) == 1
