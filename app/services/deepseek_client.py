"""DeepSeek API via OpenAI-compatible client."""

from __future__ import annotations

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


def chat_json(
    *,
    system: str,
    user: str,
    temperature: float,
    max_retries: int = 2,
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
            return extract_json(content)
        except Exception as e:  # noqa: BLE001 — surface last error after retries
            last_err = e
            continue
    assert last_err is not None
    raise last_err
