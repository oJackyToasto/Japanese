"""Import vocab and verb JSON files into SQLite."""

import json
import re
import sqlite3
from pathlib import Path


def _parse_class_no_from_vocab_filename(name: str) -> int | None:
    m = re.match(r"class(\d+)\.json$", name, re.I)
    return int(m.group(1)) if m else None


def _resolve_vocab_class_no(name: str) -> int | None:
    class_no = _parse_class_no_from_vocab_filename(name)
    if class_no is not None:
        return class_no
    return None


def _parse_class_no_from_verb_filename(name: str) -> int | None:
    m = re.match(r"class(\d+)\.json$", name, re.I)
    if m:
        return int(m.group(1))
    # Special case: intro verbs are available when class 5 is included.
    if name.lower() == "intro.json":
        return 5
    return None


def import_vocab_dir(conn: sqlite3.Connection, vocabs_dir: Path) -> int:
    """Clear and reload vocab_items from classes/vocabs/classN.json."""
    conn.execute("DELETE FROM vocab_items")
    count = 0
    if not vocabs_dir.is_dir():
        return count
    for path in sorted(vocabs_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        class_no = _resolve_vocab_class_no(path.name)

        class_word_groups: list[tuple[int, list[dict]]] = []
        if class_no is not None:
            words = data.get("words") or []
            if isinstance(words, list):
                class_word_groups.append((class_no, words))
        elif path.name.lower() == "quantity.json":
            for key, words in data.items():
                m = re.match(r"class(\d+)", str(key), re.I)
                if not m or not isinstance(words, list):
                    continue
                class_word_groups.append((int(m.group(1)), words))
            # Backward compatibility with the old quantity.json format.
            if not class_word_groups and isinstance(data.get("words"), list):
                class_word_groups.append((5, data.get("words") or []))
        else:
            continue

        for item_class_no, words in class_word_groups:
            for w in words:
                word = (w.get("word") or "").strip()
                if not word:
                    continue
                conn.execute(
                    """
                    INSERT INTO vocab_items (class_no, word, spelling, pitch, meaning)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        item_class_no,
                        word,
                        w.get("spelling"),
                        w.get("pitch"),
                        w.get("meaning"),
                    ),
                )
                count += 1
    conn.commit()
    return count


def _verbs_from_json(data: dict) -> list[dict]:
    raw = data.get("verbs") or data.get("words") or []
    return raw if isinstance(raw, list) else []


def import_verbs_dir(conn: sqlite3.Connection, verbs_dir: Path) -> int:
    conn.execute("DELETE FROM verb_items")
    count = 0
    if not verbs_dir.is_dir():
        conn.commit()
        return count
    for path in sorted(verbs_dir.glob("*.json")):
        class_no = _parse_class_no_from_verb_filename(path.name)
        if class_no is None:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for v in _verbs_from_json(data):
            lemma = (v.get("lemma") or "").strip()
            if not lemma:
                continue
            verb_display = (v.get("verb") or "").strip() or None
            vt = v.get("verb_type")
            if vt is None:
                continue
            try:
                verb_type = int(vt)
            except (TypeError, ValueError):
                continue
            conn.execute(
                """
                INSERT INTO verb_items
                (class_no, source_file, verb_display, lemma, reading, meaning, verb_type, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    class_no,
                    path.name,
                    verb_display,
                    lemma,
                    v.get("reading"),
                    v.get("meaning"),
                    verb_type,
                    v.get("notes"),
                ),
            )
            count += 1
    conn.commit()
    return count


def sync_all(conn: sqlite3.Connection, vocabs_dir: Path, verbs_dir: Path) -> tuple[int, int]:
    v = import_vocab_dir(conn, vocabs_dir)
    b = import_verbs_dir(conn, verbs_dir)
    return v, b
