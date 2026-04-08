"""Build allowed surface strings from DB and validate generated Japanese."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

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


def load_allowed_pack(
    conn: sqlite3.Cursor | sqlite3.Connection,
    class_min: int,
    class_max: int,
    verb_form_mode: str,
) -> AllowedPack:
    """verb_form_mode: 'masu' or 'lemma'."""
    tokens: set[str] = set(GRAMMAR_TOKENS)

    for row in conn.execute(
        """
        SELECT word, spelling FROM vocab_items
        WHERE class_no >= ? AND class_no <= ?
        """,
        (class_min, class_max),
    ):
        w = (row["word"] or "").strip()
        if w:
            tokens.add(w)
        sp = (row["spelling"] or "").strip() if row["spelling"] else ""
        if sp:
            tokens.add(sp)

    for row in conn.execute(
        "SELECT lemma, verb_type, verb_display FROM verb_items",
    ):
        lemma = (row["lemma"] or "").strip()
        vt = int(row["verb_type"])
        disp = (row["verb_display"] or "").strip() if row["verb_display"] else ""
        if disp:
            tokens.add(disp)
        if verb_form_mode == "lemma":
            tokens.add(lemma)
        else:
            tokens.add(masu_form(lemma, vt))

    # Longest-first greedy segmentation
    lst = sorted(tokens, key=len, reverse=True)
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
        # Allow unknown hiragana function-word chunks (particles/auxiliaries) to avoid hard-coding.
        m = re.match(r"[\u3040-\u309f]+", s[i:])
        if m:
            i += len(m.group(0))
            continue
        return False, f"Cannot match from index {i}: {s[i : i + 10]!r}..."
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
