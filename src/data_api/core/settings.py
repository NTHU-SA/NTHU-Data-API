"""
Application settings using pydantic-settings.

Settings are loaded from environment variables and .env file.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server settings
    port: int = Field(default=5000, description="Server port")
    dev_mode: bool = Field(default=False, description="Development mode")
    host: str = Field(default="0.0.0.0", description="Server host")
    workers: int = Field(default=2, description="Number of workers (production)")
    log_level: str = Field(default="error", description="Log level")

    # Data settings
    file_details_cache_expiry: int = Field(
        default=300,
        description="File details cache expiry time in seconds (default: 5 minutes)",
    )

    # API settings
    cors_origins: list[str] = Field(
        default=["*"],
        description="CORS allowed origins",
    )


# FastMCP 要開啟實驗性功能（但之後會變正式版本），不然 openapi.json 解析會有問題
os.environ["FASTMCP_EXPERIMENTAL_ENABLE_NEW_OPENAPI_PARSER"] = "true"

# Global settings instance
settings = Settings()
