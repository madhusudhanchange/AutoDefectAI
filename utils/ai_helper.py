"""
OpenAI helpers for AutoDefectAI. API key from OPENAI_API_KEY only.
"""

from __future__ import annotations

import json
import os
from typing import Tuple

# Keep titles within GitHub's limit (256); stay shorter for readability.
_MAX_TITLE_LEN = 120


def _fallback_summary(error_text: str) -> str:
    text = (error_text or "").strip()
    if not text:
        return "Unknown failure"
    first = text.split("\n", 1)[0].strip()
    return first if first else "Unknown failure"


def generate_ai_summary(test_name: str, error_text: str) -> Tuple[str, str]:
    """
    Return (issue_title, summary) for a failed test.

    Uses gpt-4o-mini with low temperature. On missing key or any failure,
    falls back to a static title and the first line of ``error_text`` as summary.
    """
    fallback_title = f"Failed: {test_name}"
    fb_summary = _fallback_summary(error_text)

    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return fallback_title, fb_summary

    err = (error_text or "").strip()
    payload = err[:12000] if err else "(no traceback)"

    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.25,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write concise GitHub issue titles and short summaries for "
                        "automated test failures. Reply with JSON only, keys title and summary."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Given this pytest failure, produce:\n"
                        "- title: short GitHub issue title (max 72 characters, no surrounding quotes)\n"
                        "- summary: 2-4 clear sentences for a human triager\n\n"
                        f"Test name: {test_name}\n\n"
                        f"Error output:\n{payload}\n\n"
                        'Return: {"title": "...", "summary": "..."}'
                    ),
                },
            ],
        )
        raw = (completion.choices[0].message.content or "").strip() or "{}"
        data = json.loads(raw)
        title = (data.get("title") or fallback_title).strip() or fallback_title
        summary = (data.get("summary") or fb_summary).strip() or fb_summary
        title = title[:_MAX_TITLE_LEN]
        return title, summary
    except Exception:
        return fallback_title, fb_summary
