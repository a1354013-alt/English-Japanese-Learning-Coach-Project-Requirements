"""Application settings for the backend."""
from pathlib import Path
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

    # Cache
    redis_url: str = "redis://localhost:6379/0"
    cache_expire: int = 3600

    # Scheduler/API
    auto_generate_time: str = "07:30"
    timezone: str = "Asia/Taipei"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS: comma-separated origins (no spaces required). Used by FastAPI CORSMiddleware.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Single-tenant demo default; override for multi-user / auth later.
    default_user_id: str = "default_user"

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


settings = Settings()
