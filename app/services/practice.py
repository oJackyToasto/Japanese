"""Orchestrate question generation and grading."""

from __future__ import annotations

import json
import random
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any

from flask import current_app

from app.services.allowed_tokens import AllowedPack, can_segment, load_allowed_pack, allowed_summary_for_prompt
from app.services.deepseek_client import chat_json


GENERATOR_SYSTEM = """你是「题目生成器」。你只输出 JSON 对象，不要 Markdown，不要多余说明。
规则：
- 难度相当于日语 N5；句子长度约 5～8 个词（日语词，不是汉字字数）。
- 只使用用户提供的「允许使用的词语」表中的词语；人名、专有名词也必须来自该表。
- 助词/功能词不做固定白名单限制；可使用自然、基础的日语助词连接句子。
- 动词优先使用 ます形；不要使用非常见变形（て形、た形、ない形、意志形、命令形），除非该整词明确在允许词表中。
- 句子必须是「可在现实语境中成立」的自然表达，避免语义冲突与搭配错误（如不合理主语-动词组合、错误宾语搭配）。
- 时间表达优先使用课内稳定模式：N時にVます / N時からN時までVます / 何時にVます。
- 若拿不准某个词是否可用，宁可不用；优先选择最基础、最稳妥搭配。
- 输出字段严格为：
  {"japanese_sentence": "...", "hint": "...", "reference_translation": "..."}
- hint 可为空字符串；如需提示，可提示某个动词的原形（用中文说明即可）。
- reference_translation 是供批改用的自然中文，不要展示给用户的说明写在该字段中。
- 生成前先在内部自检三项（不要输出自检过程）：
  1) 所有内容在允许词表中；
  2) 助词和动词搭配自然；
  3) 与常见 N5 句型一致。"""


GRADER_SYSTEM = """你是「批改老师」。你只输出 JSON 对象，不要 Markdown，不要多余说明。
评判标准：中文翻译忠实原句意思即可；助词对应的语义关系正确即可，不要求字面对译。
输出字段严格为：
{"is_correct": true/false, "feedback": "...", "correction": "..."}
若 is_correct 为 true，correction 必须为空字符串 "";
若 is_correct 为 false，correction 给出自然、标准的中文参考翻译。"""

NATURALNESS_SYSTEM = """你是日语句子质量检查器。你只输出 JSON 对象。
任务：判断给定日语句子在 N5 范围是否自然、语义通顺、助词搭配是否基本合理。
输出格式严格为：
{"is_natural": true/false, "reason": "..."}
要求：
- 若句子存在明显不自然搭配（例如助词搭配错误、语义角色冲突）则 is_natural=false。
- 若基本自然可理解则 is_natural=true。
- reason 用简短中文说明。"""


@dataclass(frozen=True)
class GenerationContext:
    pack: AllowedPack
    base_user_message: str
    focus_words: str
    mode_zh: str
    structures_summary: str
    avoid_block: str
    structure_balance_block: str
    token_summary: str


@dataclass(frozen=True)
class GenerationConfig:
    max_attempts: int = 5
    max_total_calls: int = 10
    first_attempt_temperature: float = 0.25
    retry_temperature: float = 0.15
    chat_retries_per_attempt: int = 2


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    error: str = ""
    category: str = "unknown"


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict[str, Any]) -> None:
    # region agent log
    try:
        payload = {
            "id": f"log_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
            "runId": "pre-fix",
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


def generate_question(
    conn: sqlite3.Connection,
    *,
    class_min: int,
    class_max: int,
    include_previous_vocab: bool = False,
) -> dict[str, Any]:
    _debug_log(
        "H1",
        "app/services/practice.py:generate_question",
        "enter_generate_question",
        {
            "class_min": class_min,
            "class_max": class_max,
            "include_previous_vocab": include_previous_vocab,
        },
    )
    config = GenerationConfig()
    ctx = _build_generation_context(
        conn=conn,
        class_min=class_min,
        class_max=class_max,
        include_previous_vocab=include_previous_vocab,
    )
    _debug_log(
        "H2",
        "app/services/practice.py:generate_question",
        "structures_summary_built",
        {
            "structures_preview": ctx.structures_summary[:300],
            "structures_len": len(ctx.structures_summary),
            "tokens_len": len(ctx.token_summary),
        },
    )
    _debug_log(
        "H5",
        "app/services/practice.py:generate_question",
        "diversity_constraints_built",
        {
            "avoid_len": len(ctx.avoid_block),
            "focus_words": ctx.focus_words,
        },
    )
    _debug_log(
        "H10",
        "app/services/practice.py:generate_question",
        "structure_balance_built",
        {"block": ctx.structure_balance_block[:300]},
    )
    required = ("japanese_sentence", "hint", "reference_translation")
    regen_msg = ctx.base_user_message
    seen_bad: list[str] = []
    last_error = "unknown"
    attempt = 0
    total_calls = 0
    while attempt < config.max_attempts and total_calls < config.max_total_calls:
        total_calls += 1
        current_attempt = attempt + 1
        data = chat_json(
            system=GENERATOR_SYSTEM,
            user=regen_msg,
            temperature=(
                config.first_attempt_temperature
                if current_attempt == 1
                else config.retry_temperature
            ),
            max_retries=config.chat_retries_per_attempt,
        )
        for k in required:
            if k not in data:
                raise KeyError(f"Missing key in generator JSON: {k}")
        ja = str(data["japanese_sentence"]).strip()
        if ja in seen_bad:
            last_error = "generator repeated a previously rejected sentence"
            regen_msg = (
                ctx.base_user_message
                + "\n\n你重复了已判定不合格的句子，禁止再次输出以下句子：\n"
                + "\n".join(f"- {s}" for s in seen_bad[-3:])
                + "\n请输出一个全新句子，且主语和动词都必须不同。"
            )
            continue
        attempt += 1
        _debug_log(
            "H7",
            "app/services/practice.py:generate_question",
            "generation_attempt_result",
            {"attempt": current_attempt, "total_calls": total_calls, "sentence": ja},
        )
        result = _run_validators(ja, ctx)
        if result.ok:
            return data
        if result.category == "naturalness":
            seen_bad.append(f"{ja}（不自然：{result.error}）")
            regen_msg = _build_retry_message(
                ctx.base_user_message,
                seen_bad,
                reason=result.error,
                category=result.category,
            )
            last_error = f"unnatural: {result.error}"
            continue
        _debug_log(
            "H6",
            "app/services/practice.py:generate_question",
            "validation_failed",
            {"attempt": current_attempt, "total_calls": total_calls, "sentence": ja, "error": result.error},
        )
        last_error = result.error
        seen_bad.append(ja)
        regen_msg = _build_retry_message(
            ctx.base_user_message,
            seen_bad,
            reason=result.error,
            category=result.category,
        )
    if total_calls >= config.max_total_calls and last_error == "generator repeated a previously rejected sentence":
        raise ValueError("Generated sentence failed validation repeatedly: model kept repeating rejected outputs")
    raise ValueError(f"Generated sentence failed validation repeatedly: {last_error}")


def _build_generation_context(
    *,
    conn: sqlite3.Connection,
    class_min: int,
    class_max: int,
    include_previous_vocab: bool,
) -> GenerationContext:
    token_class_min = 1 if include_previous_vocab else class_min
    pack = load_allowed_pack(conn, token_class_min, class_max)
    summary = allowed_summary_for_prompt(pack, max_items=1500)
    structures_summary = _load_structures_summary(class_min, class_max)
    avoid_block = _recent_avoidance_block(conn)
    structure_balance_block = _recent_structure_balance_block(conn)
    focus_words = _focus_words_hint(pack.tokens)

    base_user_message = (
        "动词可使用已学范围内的常见基础形态（如原形/ます形）。\n"
        f"允许使用的词语（词汇范围：第{token_class_min}课到第{class_max}课；含已学动词形态，以及名词等）：\n"
        f"{summary}\n\n"
        "允许使用的句型（按已学课次）：\n"
        f"{structures_summary}\n\n"
        "必须尽量贴合以上句型骨架，不要使用未列出的新语法结构。\n"
        "优先用最稳妥、最常见的 N5 搭配；避免生硬或罕见组合。\n"
        f"{avoid_block}\n"
        f"{structure_balance_block}\n"
        f"优先尝试包含这些词中的至少一个（若可自然造句）：{focus_words}\n"
        "请生成一道「日译中」练习题：给一句日语，让学生翻译成中文。\n"
        "硬性要求：如果你的候选句有任何不自然风险，请重写，直到自然为止。"
    )
    return GenerationContext(
        pack=pack,
        base_user_message=base_user_message,
        focus_words=focus_words,
        mode_zh="class_range_only",
        structures_summary=structures_summary,
        avoid_block=avoid_block,
        structure_balance_block=structure_balance_block,
        token_summary=summary,
    )


def _run_validators(sentence: str, ctx: GenerationContext) -> ValidationResult:
    validators = (
        _validate_allowed_tokens,
        _validate_naturalness,
    )
    for validator in validators:
        result = validator(sentence, ctx)
        if not result.ok:
            return result
    return ValidationResult(ok=True)


def _validate_allowed_tokens(sentence: str, ctx: GenerationContext) -> ValidationResult:
    ok, err = can_segment(sentence, ctx.pack)
    if ok:
        return ValidationResult(ok=True)
    return ValidationResult(ok=False, error=err, category="allowed_tokens")


def _validate_naturalness(sentence: str, _ctx: GenerationContext) -> ValidationResult:
    nat_ok, nat_reason = _is_natural_sentence(sentence)
    _debug_log(
        "H8",
        "app/services/practice.py:_validate_naturalness",
        "naturalness_check_result",
        {"sentence": sentence, "is_natural": nat_ok, "reason": nat_reason},
    )
    if nat_ok:
        return ValidationResult(ok=True)
    return ValidationResult(ok=False, error=nat_reason, category="naturalness")


def _build_retry_message(base_message: str, seen_bad: list[str], *, reason: str, category: str) -> str:
    if category == "naturalness":
        reason_line = f"\n不自然原因：{reason}\n" if reason else "\n"
        hard_ban = "\n".join(f"- {s}" for s in seen_bad[-3:])
        return (
            base_message
            + "\n\n以下句子不自然或语义不通：\n"
            + hard_ban
            + reason_line
            + "重写要求：\n"
            + "1) 绝对不要重复以上任何句子（即使只改一个词也不行）；\n"
            + "2) 必须更换关键搭配（主语/时间词/动词至少两项）；\n"
            + "3) 优先使用稳定模板：N時にVます / N時からN時までVます / NはNです；\n"
            + "4) 输出语义自然、助词搭配正确的 N5 句子。"
        )
    return (
        base_message
        + "\n\n以下句子都不合格（包含未学习词语或不在允许表中）：\n"
        + "\n".join(f"- {s}" for s in seen_bad[-3:])
        + f"\n错误示例：{reason}\n"
        + "请严格只使用允许词语表中的内容重写，尤其不要引入新的动词。"
    )


def _is_natural_sentence(sentence: str) -> tuple[bool, str]:
    data = chat_json(
        system=NATURALNESS_SYSTEM,
        user=json.dumps({"japanese_sentence": sentence}, ensure_ascii=False),
        temperature=0.0,
        max_retries=1,
    )
    raw_ok = data.get("is_natural", False)
    if isinstance(raw_ok, bool):
        ok = raw_ok
    elif isinstance(raw_ok, str):
        ok = raw_ok.strip().lower() in ("true", "1", "yes")
    else:
        ok = False
    reason = str(data.get("reason") or "")
    return ok, reason


def grade_answer(
    *,
    japanese_sentence: str,
    reference_translation: str,
    user_answer: str,
) -> dict[str, Any]:
    user_msg = json.dumps(
        {
            "japanese_sentence": japanese_sentence,
            "reference_translation": reference_translation,
            "user_translation": user_answer.strip(),
        },
        ensure_ascii=False,
    )
    return chat_json(
        system=GRADER_SYSTEM,
        user=user_msg,
        temperature=0.1,
        max_retries=2,
    )


def _load_structures_summary(class_min: int, class_max: int) -> str:
    path = current_app.config["CLASSES_SENTENCES"]
    _debug_log(
        "H2",
        "app/services/practice.py:_load_structures_summary",
        "load_structures_file",
        {"path": str(path), "exists": path.exists()},
    )
    if not path.exists():
        return "（未提供句型配置文件）"
    data = json.loads(path.read_text(encoding="utf-8"))
    class_items = data.get("classes") if isinstance(data, dict) else None
    if not isinstance(class_items, list):
        return "（句型配置格式无效）"

    lines: list[str] = []
    for cls in class_items:
        if not isinstance(cls, dict):
            continue
        class_no = cls.get("class_no")
        if not isinstance(class_no, int):
            continue
        if class_no < class_min or class_no > class_max:
            continue
        structures = cls.get("structures")
        if not isinstance(structures, list):
            continue
        for item in structures:
            if not isinstance(item, dict):
                continue
            if item.get("enabled") is False:
                continue
            pattern = str(item.get("pattern") or "").strip()
            if not pattern:
                continue
            meaning = str(item.get("meaning") or "").strip()
            note = str(item.get("notes") or "").strip()
            entry = f"[第{class_no}课] {pattern}"
            if meaning:
                entry += f"（{meaning}）"
            if note:
                entry += f"；备注：{note}"
            lines.append(entry)

    if not lines:
        _debug_log(
            "H3",
            "app/services/practice.py:_load_structures_summary",
            "no_enabled_structures_in_range",
            {"class_min": class_min, "class_max": class_max},
        )
        return "（当前课次没有启用句型，请仅用已学词汇造最基础句）"
    _debug_log(
        "H2",
        "app/services/practice.py:_load_structures_summary",
        "structures_loaded",
        {"line_count": len(lines), "class_min": class_min, "class_max": class_max},
    )
    return "\n".join(lines)


def _recent_avoidance_block(conn: sqlite3.Connection) -> str:
    rows = conn.execute(
        """
        SELECT question_json
        FROM practice_attempts
        ORDER BY id DESC
        LIMIT 8
        """
    ).fetchall()
    recent_sentences: list[str] = []
    token_freq: dict[str, int] = {}
    for r in rows:
        raw = r["question_json"] if isinstance(r, sqlite3.Row) else r[0]
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        s = str(obj.get("japanese_sentence") or "").strip()
        if not s:
            continue
        recent_sentences.append(s)
        for t in re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]+", s):
            if len(t) <= 1:
                continue
            token_freq[t] = token_freq.get(t, 0) + 1
    if not recent_sentences:
        return "多样性要求：尽量不要连续两题使用相同主语与场所。"
    hot = sorted(token_freq.items(), key=lambda x: x[1], reverse=True)[:5]
    hot_tokens = [k for k, _v in hot]
    exact = " / ".join(recent_sentences[:3])
    return (
        "多样性要求：避免与最近题目重复。\n"
        f"- 不要与这些句子完全相同：{exact}\n"
        f"- 尽量避免重复高频词：{'、'.join(hot_tokens) if hot_tokens else '（无）'}"
    )


def _focus_words_hint(tokens: list[str]) -> str:
    candidates = [
        t
        for t in tokens
        if len(t) >= 2 and all(ch not in "。、！？「」『』（）・ー〜 " for ch in t)
    ]
    if not candidates:
        return "（无）"
    pick = random.sample(candidates, k=min(8, len(candidates)))
    return "、".join(pick)


def _recent_structure_balance_block(conn: sqlite3.Connection) -> str:
    rows = conn.execute(
        """
        SELECT question_json
        FROM practice_attempts
        ORDER BY id DESC
        LIMIT 12
        """
    ).fetchall()
    counts: dict[str, int] = {"existence": 0, "copula": 0, "question": 0, "other": 0}
    total = 0
    for r in rows:
        raw = r["question_json"] if isinstance(r, sqlite3.Row) else r[0]
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        s = str(obj.get("japanese_sentence") or "").strip()
        if not s:
            continue
        if "あります" in s or "います" in s:
            counts["existence"] += 1
        elif "ですか" in s or s.endswith("か。") or "どこ" in s or "なに" in s:
            counts["question"] += 1
        elif "です" in s:
            counts["copula"] += 1
        else:
            counts["other"] += 1
        total += 1
    if total == 0:
        return "句型多样性：尽量避免连续使用同一类型句型。"
    ex_ratio = counts["existence"] / total
    cp_ratio = counts["copula"] / total
    if ex_ratio >= 0.40:
        return (
            "句型多样性要求：最近题目里「存在句（NにNがあります/います）」过多。"
            "本题请优先改用其他已学句型（如 判断句 NはNです、疑问句、时间+动词句），"
            "避免再次使用存在句。"
        )
    if cp_ratio >= 0.55:
        return "句型多样性要求：最近判断句过多。本题优先使用疑问句或时间+动词句，避免继续用 NはNです。"
    return "句型多样性：避免与最近题目重复同一类型句型。"
