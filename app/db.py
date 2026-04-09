"""SQLite persistence: schema init and low-level helpers."""

import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS vocab_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_no INTEGER NOT NULL,
    word TEXT NOT NULL,
    spelling TEXT,
    pitch INTEGER,
    meaning TEXT
);

CREATE TABLE IF NOT EXISTS verb_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_no INTEGER NOT NULL,
    source_file TEXT NOT NULL,
    verb_display TEXT,
    lemma TEXT NOT NULL,
    reading TEXT,
    meaning TEXT,
    verb_type INTEGER NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS practice_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    mode TEXT NOT NULL,
    class_min INTEGER NOT NULL,
    class_max INTEGER NOT NULL,
    question_json TEXT NOT NULL,
    user_answer TEXT NOT NULL,
    grading_json TEXT NOT NULL,
    correct INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS question_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    cache_key TEXT NOT NULL,
    class_min INTEGER NOT NULL,
    class_max INTEGER NOT NULL,
    include_previous_vocab INTEGER NOT NULL,
    question_json TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_vocab_class ON vocab_items(class_no);
CREATE INDEX IF NOT EXISTS idx_attempts_created ON practice_attempts(created_at);
CREATE INDEX IF NOT EXISTS idx_cache_lookup ON question_cache(cache_key, used, id);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        path = Path(current_app.config["DB_PATH"])
        path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(str(path), detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_e: Any = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app: Flask) -> None:
    app.teardown_appcontext(close_db)

    db_path: Path = app.config["DB_PATH"]
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(verb_items)").fetchall()]
        if "class_no" not in cols:
            conn.execute("ALTER TABLE verb_items ADD COLUMN class_no INTEGER NOT NULL DEFAULT 1")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_verbs_class ON verb_items(class_no)")
        conn.commit()
    finally:
        conn.close()
