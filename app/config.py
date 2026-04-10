"""Application configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


_repo = _repo_root()
load_dotenv(_repo / ".env")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-change-me")

    REPO_ROOT = _repo
    CLASSES_VOCABS = REPO_ROOT / "classes" / "vocabs"
    CLASSES_VERBS = REPO_ROOT / "classes" / "verbs"
    CLASSES_SENTENCES = REPO_ROOT / "classes" / "sentences" / "sentence.json"
    DB_PATH = REPO_ROOT / "app" / "data" / "learning.db"
    LOG_DIR = REPO_ROOT / "app" / "logs"
    LOG_PATH = LOG_DIR / "app.log"
    COST_LOG_PATH = LOG_DIR / "cost.log"
    LOG_LEVEL = os.environ.get("APP_LOG_LEVEL", "INFO")
    DEBUG = _env_bool("FLASK_DEBUG", True)
    TEMPLATES_AUTO_RELOAD = True

    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    # Question generation retries after validator failure:
    # "detailed" = append reasons + long rewrite instructions (default).
    # "minimal" = short instruction + banned sentences only (fewer tokens; A/B vs detailed).
    PRACTICE_REGEN_PROMPT = os.environ.get("PRACTICE_REGEN_PROMPT", "detailed").strip().lower()
