"""Application settings for the backend."""
from pathlib import Path

from chat_contract import CHAT_CLIENT_MESSAGE_ID_MAX_CHARS
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Ollama
    ollama_url: str = "http://localhost:11434"
    model_name: str = "llama2:13b"
    small_model_name: str = "llama3:8b"
    large_model_name: str = "llama2:13b"

    # Storage
    data_dir: str = str(DEFAULT_DATA_DIR)
    db_path: str = str(DEFAULT_DATA_DIR / "language_coach.db")
    chroma_db_path: str = str(DEFAULT_DATA_DIR / "chroma_db")
    enable_rag: bool = False
    allow_demo_reset: bool = False
    max_upload_size_mb: int = 10

    # Cache
    redis_url: str = "redis://localhost:6379/0"
    cache_expire: int = 3600

    # Scheduler/API
    auto_generate_time: str = "07:30"
    timezone: str = "Asia/Taipei"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    # CORS: comma-separated origins (no spaces required). Used by FastAPI CORSMiddleware.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Single-tenant demo default; override for multi-user / auth later.
    default_user_id: str = "default_user"
    chat_recent_message_limit: int = 20
    chat_context_max_chars: int = 12000
    chat_message_max_chars: int = 8000
    chat_assistant_response_max_chars: int = 12000
    chat_client_message_id_max_chars: int = CHAT_CLIENT_MESSAGE_ID_MAX_CHARS

    @model_validator(mode="after")
    def validate_chat_runtime_settings(self) -> "Settings":
        if self.chat_recent_message_limit <= 0:
            raise ValueError("chat_recent_message_limit must be > 0")
        if self.chat_context_max_chars < 100:
            raise ValueError("chat_context_max_chars must be at least 100")
        if self.chat_message_max_chars <= 0:
            raise ValueError("chat_message_max_chars must be > 0")
        if self.chat_assistant_response_max_chars <= 0:
            raise ValueError("chat_assistant_response_max_chars must be > 0")
        if self.chat_client_message_id_max_chars <= 0:
            raise ValueError("chat_client_message_id_max_chars must be > 0")
        if self.chat_client_message_id_max_chars > CHAT_CLIENT_MESSAGE_ID_MAX_CHARS:
            raise ValueError(
                "chat_client_message_id_max_chars must leave room for the user: idempotency prefix"
            )
        return self

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir).resolve()

    @property
    def lessons_dir(self) -> Path:
        return self.data_path / "lessons"

    @property
    def audio_dir(self) -> Path:
        return self.data_path / "audio"

    @property
    def exports_dir(self) -> Path:
        return self.data_path / "exports"

    @property
    def max_upload_size_bytes(self) -> int:
        return max(0, self.max_upload_size_mb) * 1024 * 1024


settings = Settings()
