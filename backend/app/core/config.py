from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录：backend/app/core/config.py -> 向上 4 级即 agentops 根目录（.env 所在处）
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """应用配置：从项目根目录的 .env 读取，字段对应 .env.example 中的变量名。"""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # PostgreSQL（本地 Docker 运行）
    database_url: str = "postgresql+psycopg://agentops:agentops@localhost:5432/agentops"
    # LLM 网关（Layer 2 起使用）
    deepseek_api_key: str = ""
    backup_model_key: str = ""
    openrouter_key: str = ""            # 视觉模型 key（OpenRouter）
    # LLM 模型（LiteLLM 格式：provider/model）
    llm_model: str = "deepseek/deepseek-v4-flash"
    vision_model: str = "openrouter/qwen/qwen2.5-vl-72b-instruct"  # 视觉模型（真实小票已验证）
    # 前端地址（CORS，Layer 8 起使用）
    frontend_url: str = "http://localhost:5173"


settings = Settings()
