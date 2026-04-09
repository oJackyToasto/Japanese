"""HTTP routes for practice flow."""

from __future__ import annotations

import json
import sqlite3

from flask import (
    Blueprint,
    flash,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.db import get_db
from app.importer import sync_all
from app.services.practice import generate_question, grade_answer

bp = Blueprint("main", __name__, url_prefix="")


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    return


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "是")
    return False


def _as_form_bool(value: object) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _row_count(conn: sqlite3.Connection, table: str) -> int:
    cur = conn.execute(f"SELECT COUNT(*) AS c FROM {table}")
    return int(cur.fetchone()["c"])


def _row_count_in_range(conn: sqlite3.Connection, table: str, class_min: int, class_max: int) -> int:
    cur = conn.execute(
        f"SELECT COUNT(*) AS c FROM {table} WHERE class_no >= ? AND class_no <= ?",
        (class_min, class_max),
    )
    return int(cur.fetchone()["c"])


@bp.route("/", methods=["GET"])
def index():
    return render_template(
        "index.html",
        current=session.get("current_question"),
        last=session.get("last_result"),
    )


@bp.route("/generate", methods=["POST"])
def generate():
    try:
        class_min = int(request.form.get("class_min", "1"))
        class_max = int(request.form.get("class_max", "4"))
    except (TypeError, ValueError):
        flash("课次范围无效。", "error")
        return redirect(url_for("main.index"))
    class_min = max(1, min(class_min, 99))
    class_max = max(class_min, min(class_max, 99))
    include_previous_vocab = _as_form_bool(request.form.get("include_previous_vocab"))
    _debug_log(
        "H1",
        "app/routes.py:generate",
        "generate_request_received",
        {
            "class_min": class_min,
            "class_max": class_max,
            "include_previous_vocab": include_previous_vocab,
        },
    )

    conn = get_db()
    if _row_count(conn, "vocab_items") == 0:
        flash("数据库为空。请在项目目录运行：flask --app run sync-data", "error")
        return redirect(url_for("main.index"))
    # If selected class range has no data (e.g. after schema/import rule change),
    # auto re-sync from JSON once to self-heal stale local DB.
    vocab_in_range = _row_count_in_range(conn, "vocab_items", class_min, class_max)
    verbs_in_range = _row_count_in_range(conn, "verb_items", class_min, class_max)
    if vocab_in_range == 0 or verbs_in_range == 0:
        sync_all(conn, current_app.config["CLASSES_VOCABS"], current_app.config["CLASSES_VERBS"])
        vocab_in_range = _row_count_in_range(conn, "vocab_items", class_min, class_max)
        verbs_in_range = _row_count_in_range(conn, "verb_items", class_min, class_max)
        if vocab_in_range == 0 or verbs_in_range == 0:
            flash(
                "所选课次范围缺少词汇或动词数据。请运行：flask --app run sync-data",
                "error",
            )
            return redirect(url_for("main.index"))

    session.pop("last_result", None)
    try:
        data = generate_question(
            conn,
            class_min=class_min,
            class_max=class_max,
            include_previous_vocab=include_previous_vocab,
        )
    except Exception as e:  # noqa: BLE001
        current_app.logger.warning(
            "question_generation failed class_min=%s class_max=%s include_previous_vocab=%s error=%s",
            class_min,
            class_max,
            include_previous_vocab,
            e,
        )
        flash(f"出题失败：{e}", "error")
        return redirect(url_for("main.index"))
    current_app.logger.info(
        "question_generation success class_min=%s class_max=%s include_previous_vocab=%s sentence=%s",
        class_min,
        class_max,
        include_previous_vocab,
        str(data.get("japanese_sentence") or ""),
    )

    session["current_question"] = {
        "japanese_sentence": data["japanese_sentence"],
        "hint": data.get("hint") or "",
        "reference_translation": data["reference_translation"],
        "class_min": class_min,
        "class_max": class_max,
        "include_previous_vocab": include_previous_vocab,
    }
    return redirect(url_for("main.index"))


@bp.route("/submit", methods=["POST"])
def submit():
    q = session.get("current_question")
    if not q:
        flash("没有进行中的题目，请先生成。", "error")
        return redirect(url_for("main.index"))
    user_answer = (request.form.get("user_answer") or "").strip()
    if not user_answer:
        flash("请输入中文翻译。", "error")
        return redirect(url_for("main.index"))

    try:
        grading = grade_answer(
            japanese_sentence=str(q["japanese_sentence"]),
            reference_translation=str(q["reference_translation"]),
            user_answer=user_answer,
        )
    except Exception as e:  # noqa: BLE001
        flash(f"批改失败：{e}", "error")
        return redirect(url_for("main.index"))

    for key in ("is_correct", "feedback", "correction"):
        if key not in grading:
            flash(f"批改结果缺少字段：{key}", "error")
            return redirect(url_for("main.index"))

    grading = dict(grading)
    grading["is_correct"] = _as_bool(grading.get("is_correct"))

    conn = get_db()
    conn.execute(
        """
        INSERT INTO practice_attempts
        (mode, class_min, class_max, question_json, user_answer, grading_json, correct)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "class_range_only",
            int(q["class_min"]),
            int(q["class_max"]),
            json.dumps(
                {
                    "japanese_sentence": q["japanese_sentence"],
                    "hint": q.get("hint") or "",
                    "reference_translation": q["reference_translation"],
                },
                ensure_ascii=False,
            ),
            user_answer,
            json.dumps(grading, ensure_ascii=False),
            1 if grading["is_correct"] else 0,
        ),
    )
    conn.commit()

    session.pop("current_question", None)
    session["last_result"] = {
        "question": q,
        "user_answer": user_answer,
        "grading": grading,
    }
    return redirect(url_for("main.index"))
