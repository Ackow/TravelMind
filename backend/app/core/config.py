from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


# 应用配置：可通过环境变量或 backend/.env 覆盖
class Settings(BaseSettings):
    app_name: str = "TravelMind API"
    app_version: str = "0.1.0"
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file="backend/.env",
        env_prefix="TRAVELMIND_",
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
