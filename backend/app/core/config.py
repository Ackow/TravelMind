from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


# 应用配置：可通过环境变量或 backend/.env 覆盖
class Settings(BaseSettings):
    app_name: str = "TravelMind API"
    app_version: str = "0.1.0"
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"
    DATA_PROVIDER_MODE: Literal["mock", "live"] = "mock"
    AMAP_API_KEY: str | None = None
    QWEATHER_API_KEY: str | None = None
    QWEATHER_HOST: str | None = None
    # 数据库持久化配置
    DATABASE_URL: str = "sqlite:///./travelmind.db"
    DATABASE_ECHO: bool = False
    USE_SQL_REPOSITORY: bool = False
    AGENT_CHECKPOINT_DB_PATH: str = "agent_checkpoints.db"

    # LLM 模型与 API 配置
    LLM_API_KEY: str | None = None
    LLM_BASE_URL: str | None = None
    LLM_MODEL: str = "gpt-4o"

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        # 把逗号分隔的 CORS 配置解析成列表，并过滤空项
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """获取设置"""
    return Settings()
