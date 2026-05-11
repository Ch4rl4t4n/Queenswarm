"""JSON salvage helpers kept free of LiteLLM or Pydantic Settings imports."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_breaker_json(raw: str) -> dict[str, Any]:
    """Return the first top-level JSON object embedded in noisy LLM text."""

    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, count=1, flags=re.IGNORECASE).strip()
        if text.endswith("```"):
            text = text[: text.rfind("```")].strip()
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    msg = "Workflow breaker model did not return a JSON object."
    raise ValueError(msg)
