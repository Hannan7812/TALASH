from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
# Load project-level .env so CLI and API runs share the same environment values.
load_dotenv(PROJECT_ROOT / ".env")


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_database_url(url: str) -> str:
    # Supabase often provides postgres:// URLs. SQLAlchemy expects postgresql+psycopg://.
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Settings:
    PROJECT_ROOT = PROJECT_ROOT
    BACKEND_ROOT = PROJECT_ROOT / "backend"
    DATA_DIR = BACKEND_ROOT / "data"
    RAW_CV_DIR = DATA_DIR / "raw_cvs"
    PARSED_JSON_DIR = DATA_DIR / "parsed_json"
    EXPORT_DIR = DATA_DIR / "exports"
    DB_PATH = BACKEND_ROOT / "talash.db"
    SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "")
    DATABASE_URL = _normalize_database_url(
        os.getenv("DATABASE_URL", SUPABASE_DB_URL or f"sqlite:///{DB_PATH}")
    )
    AUTO_INIT_DB = _as_bool(os.getenv("AUTO_INIT_DB", "false"), default=False)

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    LLM_MAX_JSON_RETRIES = int(os.getenv("LLM_MAX_JSON_RETRIES", "3"))
    LLM_REQUEST_PAUSE_SECONDS = float(os.getenv("LLM_REQUEST_PAUSE_SECONDS", "5.0"))


settings = Settings()
