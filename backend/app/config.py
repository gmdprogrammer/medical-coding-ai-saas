import json
import os
from functools import lru_cache
from typing import Any, List
from urllib.parse import urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_env: str = "development"
    app_name: str = "Medical Coding AI"
    app_version: str = "1.0.0"
    debug: bool = False
    allowed_origins: List[str] = ["http://localhost:3000"]

    # ── Security ──────────────────────────────────────────────────────────────
    # Default is INSECURE — override with a real random 256-bit key in production
    secret_key: str = "dev-insecure-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/medical_coding"
    sync_database_url: str = "postgresql://postgres:password@localhost:5432/medical_coding"

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Groq API ──────────────────────────────────────────────────────────────
    # Set GROQ_API_KEY in .env — get a free key at console.groq.com
    groq_api_key: str = "placeholder-set-groq-api-key-in-env"
    groq_model: str = "llama-3.3-70b-versatile"
    groq_max_tokens: int = 2048
    groq_temperature: float = 0.1

    # ── Vector Store ──────────────────────────────────────────────────────────
    vector_store_path: str = "./data/vector_stores"
    faiss_index_path: str = "./data/vector_stores/faiss_index"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # ── RAG ───────────────────────────────────────────────────────────────────
    rag_top_k: int = 10
    rag_similarity_threshold: float = 0.7

    # ── PHI ───────────────────────────────────────────────────────────────────
    spacy_model: str = "en_core_web_sm"   # sm ships with the repo; lg is optional
    phi_anonymization_enabled: bool = True

    # ── Data Paths ─────────────────────────────────────────────────────────────
    icd10_data_path: str = "./data/icd10"
    cpt_data_path: str = "./data/cpt"
    hcpcs_data_path: str = "./data/hcpcs"

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> List[str]:
        """
        Accept both JSON-array and comma-separated env var formats:
          ALLOWED_ORIGINS=http://localhost:3000,https://app.example.com
          ALLOWED_ORIGINS=["http://localhost:3000","https://app.example.com"]
        """
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return [str(v)]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @field_validator("database_url", "sync_database_url", mode="after")
    @classmethod
    def remap_docker_hostname_for_local(cls, v: str) -> str:
        """
        Local dev runs backend on host OS, where Docker service DNS names
        like `postgres` are not resolvable. Remap to localhost outside production.
        """
        if os.getenv("APP_ENV", "development").lower() == "production":
            return v
        parsed = urlsplit(v)
        if parsed.hostname != "postgres":
            return v
        netloc = parsed.netloc.replace("@postgres:", "@localhost:")
        if parsed.netloc.endswith("@postgres"):
            netloc = parsed.netloc[:-len("@postgres")] + "@localhost"
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


@lru_cache
def get_settings() -> Settings:
    return Settings()
