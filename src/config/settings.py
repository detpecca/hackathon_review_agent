"""
统一配置管理 - Pydantic Settings V2
所有配置从环境变量读取，支持.env文件
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用基础
    app_name: str = "HackathonReviewAgent"
    env: str = "development"
    debug: bool = False
    secret_key: str = "change-me"

    # 数据库
    database_url: str = "postgresql://hackathon:hackathon_pass@localhost:5432/hackathon_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "hackathon_minio"
    minio_secret_key: str = "hackathon_minio_secret"
    minio_secure: bool = False
    minio_bucket_submissions: str = "submissions"
    minio_bucket_reports: str = "reports"

    # LLM Keys
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    google_api_key: Optional[str] = None
    google_model: str = "gemini-2.5-flash"
    qwen_api_key: Optional[str] = None
    qwen_model: str = "qwen3-72b"
    openai_embedding_model: str = "text-embedding-3-large"

    # 沙箱配置
    sandbox_docker_host: str = "tcp://localhost:2375"
    sandbox_cpu_limit: str = "2"
    sandbox_memory_limit: str = "4g"
    sandbox_timeout: int = 600
    sandbox_max_concurrent: int = 10

    # 评审配置
    verifier_k: int = 5
    verifier_granularity: int = 20
    confidence_threshold: float = 0.80
    variance_threshold: float = 225  # 15^2

    # 日志
    log_level: str = "INFO"

    @property
    def is_development(self) -> bool:
        return self.env == "development"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例（缓存）"""
    return Settings()
