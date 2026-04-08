"""Application configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


_repo = _repo_root()
load_dotenv(_repo / ".env")


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-change-me")

    REPO_ROOT = _repo
    CLASSES_VOCABS = REPO_ROOT / "classes" / "vocabs"
    CLASSES_VERBS = REPO_ROOT / "classes" / "verbs"
    CLASSES_SENTENCES = REPO_ROOT / "classes" / "sentences" / "sentence.json"
    DB_PATH = REPO_ROOT / "app" / "data" / "learning.db"

    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
