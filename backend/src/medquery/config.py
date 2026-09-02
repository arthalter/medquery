from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从本地环境读取 Demo 运行参数。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "智药问点"
    app_env: str = "demo"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    frontend_dir: Path = Path("/app/static")
    data_dir: Path = Path("/app/data")

    session_history_rounds: int = 6
    max_atomic_questions: int = 5
    chunk_char_limit: int = 400
    chunk_overlap_last_sentence: bool = True

    milvus_uri: Path = Path("/data/milvus/medquery.db")
    milvus_collection: str = "drug_instructions"
    dense_top_k: int = 10

    bailian_region: str = "cn-beijing"
    bailian_workspace_id: str = ""
    bailian_api_key: SecretStr = SecretStr("")
    bailian_embedding_model: str = "text-embedding-v4"
    bailian_embedding_dimensions: int = 1024
    bailian_rerank_model: str = "qwen3-rerank"
    rerank_top_k: int = 3
    rerank_min_score: float = 0.0

    grok_base_url: str = ""
    grok_api_key: SecretStr = SecretStr("")
    grok_model: str = "grok-4.6"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
