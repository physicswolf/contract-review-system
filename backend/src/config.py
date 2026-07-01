from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"


class Settings(BaseSettings):
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    api_prefix: str = "/api"
    upload_dir: Path = Path("storage/uploads")
    parsing_dir: Path = Path("storage/parsing")
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "aizhiqi"
    max_upload_size_mb: int = Field(default=50, gt=0)
    docx_parser_engine: str = "docling"
    pdf_parser_engine: str = "docling"
    jwt_secret_key: str = "change-me-in-production-32-byte-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    enable_structure_editor: bool = False
    llm_api_url: str = "http://localhost:11434/v1/chat/completions"
    llm_api_key: str = "ollama"
    llm_model_name: str = "qwen3:32b"
    llm_classify_timeout: int = Field(default=10, gt=0)
    llm_classify_log_enabled: bool = False
    llm_classify_log_file: Path = Path("logs/llm_classifier.log")

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def upload_root(self) -> Path:
        path = self.upload_dir
        if not path.is_absolute():
            path = BASE_DIR / path
        return path.resolve()

    @property
    def parsing_root(self) -> Path:
        path = self.parsing_dir
        if not path.is_absolute():
            path = BASE_DIR / path
        return path.resolve()

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def llm_classify_log_path(self) -> Path:
        path = self.llm_classify_log_file
        if not path.is_absolute():
            path = BASE_DIR / path
        return path.resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
