"""
Configuration module — Single source of truth for all settings.
Uses pydantic-settings for type-safe environment variable loading.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────
    groq_api_key: str = ""
    llm_model_name: str = "llama-3.3-70b-versatile"

    # ── Embeddings ───────────────────────────────────────
    embedding_model_name: str = "all-MiniLM-L6-v2"

    # ── ChromaDB ─────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection_name: str = "documents"

    # ── Chunking ─────────────────────────────────────────
    chunk_size: int = 512
    chunk_overlap: int = 50

    # ── Retrieval ────────────────────────────────────────
    top_k_results: int = 5
    similarity_threshold: float = 0.3

    # ── Application ──────────────────────────────────────
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50

    # ── Auth (Phase 8) ───────────────────────────────────
    jwt_secret_key: str = "change_this_to_a_strong_secret"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def chroma_path(self) -> Path:
        path = Path(self.chroma_persist_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


# Singleton instance — import this everywhere
settings = Settings()
