"""Build allowed surface strings from DB and validate generated Japanese."""

from __future__ import annotations

import json
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass

from flask import current_app

from app.services.verb_masu import masu_form

# Particles and glue allowed beyond imported vocab (N5 simple patterns).
GRAMMAR_TOKENS = frozenset(
    {
        "は",
        "が",
        "を",
        "に",
        "で",
        "と",
        "の",
        "も",
        "か",
        "や",
        "から",
        "まで",
        "へ",
        "より",
        "ね",
        "よ",
        "です",
        "だ",
        "である",
        "ます",
        "ません",
        "でした",
        "ました",
        "ではありません",
        "じゃありません",
        "さん",
        "くん",
        "、",
        "。",
        "！",
        "？",
        "・",
        " ",
        "　",
        "…",
        "ー",
        "〜",
        "「",
        "」",
        "『",
        "』",
        "（",
        "）",
        "：",
        "；",
    }
)


@dataclass
class AllowedPack:
    tokens: list[str]
    sorted_by_len: list[str]


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    # region agent log
    try:
        payload = {
            "id": f"log_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
            "runId": "debug-3",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        log_path = current_app.config["REPO_ROOT"] / ".cursor" / "debug.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # endregion


def _normalized_variants(token: str) -> set[str]:
    """Generate safe surface variants for annotated vocab like '森(姓)'."""
    out = {token}
    # Support both half-width and full-width annotation brackets.
    stripped = re.sub(r"[\(（][^\)）]*[\)）]", "", token).strip()
    if stripped:
        out.add(stripped)
    return out


def load_allowed_pack(
    conn: sqlite3.Cursor | sqlite3.Connection,
    class_min: int,
    class_max: int,
) -> AllowedPack:
    """Build allowed token pack from class range, with common verb forms."""
    tokens: set[str] = set(GRAMMAR_TOKENS)
    vocab_rows = 0
    verb_rows = 0

    for row in conn.execute(
        """
        SELECT word, spelling FROM vocab_items
        WHERE class_no >= ? AND class_no <= ?
        """,
        (class_min, class_max),
    ):
        vocab_rows += 1
        w = (row["word"] or "").strip()
        if w:
            tokens.update(_normalized_variants(w))
        sp = (row["spelling"] or "").strip() if row["spelling"] else ""
        if sp:
            tokens.update(_normalized_variants(sp))

    for row in conn.execute(
        """
        SELECT lemma, verb_type, verb_display
        FROM verb_items
        WHERE class_no >= ? AND class_no <= ?
        """,
        (class_min, class_max),
    ):
        verb_rows += 1
        lemma = (row["lemma"] or "").strip()
        vt = int(row["verb_type"])
        disp = (row["verb_display"] or "").strip() if row["verb_display"] else ""
        if disp:
            tokens.update(_normalized_variants(disp))
        tokens.update(_normalized_variants(lemma))
        tokens.update(_normalized_variants(masu_form(lemma, vt)))

    # Longest-first greedy segmentation
    lst = sorted(tokens, key=len, reverse=True)
    _debug_log(
        "D1",
        "app/services/allowed_tokens.py:load_allowed_pack",
        "allowed_pack_stats",
        {
            "class_min": class_min,
            "class_max": class_max,
            "vocab_rows_in_range": vocab_rows,
            "verb_rows_in_range": verb_rows,
            "has_jin_surname_kanji": "金" in tokens,
            "has_jin_surname_annotated": "金(姓)" in tokens,
            "has_mori_surname_kanji": "森" in tokens,
            "has_shichiji": "七時" in tokens,
            "has_benkyo_shimasu": "勉強します" in tokens,
            "token_count": len(tokens),
        },
    )
    return AllowedPack(tokens=list(tokens), sorted_by_len=lst)


def can_segment(sentence: str, pack: AllowedPack) -> tuple[bool, str]:
    """Return (ok, remainder_or_empty)."""
    s = sentence.strip()
    i = 0
    n = len(s)
    while i < n:
        matched = False
        for tok in pack.sorted_by_len:
            if not tok:
                continue
            if s.startswith(tok, i):
                i += len(tok)
                matched = True
                break
        if matched:
            continue
        ch = s[i]
        if ch.isspace():
            i += 1
            continue
        chunk = s[i : i + 10]
        _debug_log(
            "D2",
            "app/services/allowed_tokens.py:can_segment",
            "segment_failed",
            {
                "sentence": s,
                "index": i,
                "chunk": chunk,
                "first_char": s[i] if i < len(s) else "",
            },
        )
        return False, f"Cannot match from index {i}: {chunk!r}..."
    return True, ""


def allowed_summary_for_prompt(pack: AllowedPack, max_items: int = 200) -> str:
    """Subset of tokens for prompt size; prefer longer multi-char items."""
    # Exclude single-char grammar except common particles we want explicit
    candidates = [t for t in pack.sorted_by_len if len(t) >= 2]
    # Still include single kana particles that are in GRAMMAR_TOKENS
    singles = [t for t in pack.sorted_by_len if len(t) == 1 and t in GRAMMAR_TOKENS]
    merged = candidates + singles
    seen: set[str] = set()
    out: list[str] = []
    for t in merged:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= max_items:
            break
    return "、".join(out)
