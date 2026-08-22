"""Application configuration."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings, overridable via env vars."""

    app_name: str = "Graph App"
    version: str = "0.1.0"

    # Paths (relative to repo root: graph-app/)
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    db_path: Path = Path(__file__).resolve().parents[2] / "data" / "app.db"
    uploads_dir: Path = Path(__file__).resolve().parents[2] / "data" / "uploads"

    # Server
    host: str = "0.0.0.0"
    port: int = 8765

    # CORS
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(env_prefix="GRAPH_APP_", env_file=".env", extra="ignore")

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
