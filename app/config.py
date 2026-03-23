from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    tavily_api_key: str = Field(..., alias="TAVILY_API_KEY")

    gemini_model: str = Field("gemini-2.5-flash", alias="GEMINI_MODEL")

    tavily_search_depth: str = Field("basic", alias="TAVILY_SEARCH_DEPTH")
    tavily_max_results: int = Field(5, alias="TAVILY_MAX_RESULTS")
    tavily_timeout_seconds: int = Field(20, alias="TAVILY_TIMEOUT_SECONDS")

    max_subquestions: int = Field(6, alias="MAX_SUBQUESTIONS")
    max_concurrent_searches: int = Field(3, alias="MAX_CONCURRENT_SEARCHES")
    log_level: str = Field("INFO", alias="LOG_LEVEL")


def get_settings() -> Settings:
    return Settings()