"""DeepSeek API via OpenAI-compatible client."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from flask import current_app
from openai import OpenAI

from app.services.json_extract import extract_json


def _client() -> OpenAI:
    key = current_app.config.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set")
    return OpenAI(
        api_key=key,
        base_url=current_app.config["DEEPSEEK_BASE_URL"],
    )


def _summarize_result(payload: dict[str, Any]) -> str:
    if "japanese_sentence" in payload:
        return str(payload.get("japanese_sentence") or "")
    if "is_natural" in payload:
        return f"is_natural={payload.get('is_natural')} reason={payload.get('reason') or ''}"
    if "is_correct" in payload:
        return f"is_correct={payload.get('is_correct')} correction={payload.get('correction') or ''}"
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return text[:200]


def chat_json(
    *,
    system: str,
    user: str,
    temperature: float,
    max_retries: int = 2,
    usage_kind: str = "chat_json",
) -> dict[str, Any]:
    """Call chat completions and parse JSON object; retry on failure."""
    model = current_app.config["DEEPSEEK_MODEL"]
    last_err: Exception | None = None
    attempts = max_retries + 1
    for _ in range(attempts):
        try:
            resp = _client().chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
            )
            content = (resp.choices[0].message.content or "").strip()
            parsed = extract_json(content)
            usage = getattr(resp, "usage", None)
            if usage is not None:
                pt = getattr(usage, "prompt_tokens", None)
                ct = getattr(usage, "completion_tokens", None)
                tt = getattr(usage, "total_tokens", None)
                logging.getLogger("app.cost").info(
                    "%s\t%s\t%s\t%s\t%s\t%s",
                    usage_kind,
                    model,
                    pt,
                    ct,
                    tt,
                    _summarize_result(parsed),
                )
            return parsed
        except Exception as e:  # noqa: BLE001 — surface last error after retries
            last_err = e
            continue
    assert last_err is not None
    raise last_err
