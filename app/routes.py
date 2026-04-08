"""HTTP routes for practice flow."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.db import get_db
from app.services.practice import generate_question, grade_answer

bp = Blueprint("main", __name__, url_prefix="")


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
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
        from flask import current_app

        log_path = current_app.config["REPO_ROOT"] / ".cursor" / "debug.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # endregion


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "是")
    return False


def _row_count(conn: sqlite3.Connection, table: str) -> int:
    cur = conn.execute(f"SELECT COUNT(*) AS c FROM {table}")
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
    mode = (request.form.get("verb_form_mode") or "masu").strip()
    if mode not in ("masu", "lemma"):
        mode = "masu"
    _debug_log(
        "H1",
        "app/routes.py:generate",
        "generate_request_received",
        {"class_min": class_min, "class_max": class_max, "mode": mode},
    )

    conn = get_db()
    if _row_count(conn, "vocab_items") == 0:
        flash("数据库为空。请在项目目录运行：flask --app run sync-data", "error")
        return redirect(url_for("main.index"))

    session.pop("last_result", None)
    try:
        data = generate_question(
            conn,
            class_min=class_min,
            class_max=class_max,
            verb_form_mode=mode,
        )
    except Exception as e:  # noqa: BLE001
        flash(f"出题失败：{e}", "error")
        return redirect(url_for("main.index"))

    session["current_question"] = {
        "japanese_sentence": data["japanese_sentence"],
        "hint": data.get("hint") or "",
        "reference_translation": data["reference_translation"],
        "class_min": class_min,
        "class_max": class_max,
        "verb_form_mode": mode,
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
            q["verb_form_mode"],
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
