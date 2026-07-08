"""
StructuredOutputEngine: turns a raw LLM string into a validated
`StructuredOutput`, with best-effort recovery when the model doesn't
return clean JSON.

`LLMClient.generate_json` (core/llm_client.py) already does one corrective
re-prompt at the transport layer. This engine is the second, cheaper line
of defense — string-level cleanup that doesn't cost another LLM call —
plus the schema-validation step that turns a raw dict into a typed,
task-specific Pydantic model.
"""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.agents.exceptions import StructuredOutputParseError
from app.agents.types import StructuredOutput

T = TypeVar("T", bound=BaseModel)

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


class StructuredOutputEngine:
    """Stateless helper — safe to share a single instance across agents."""

    @staticmethod
    def parse_json(raw: str) -> dict:
        """Parse `raw` as JSON, attempting cheap recovery before giving up.

        Recovery steps (in order): strip markdown code fences, strip a
        leading/trailing prose wrapper by extracting the outermost
        `{...}` span, and remove trailing commas — the most common ways an
        LLM's "JSON" response fails to parse verbatim.
        """
        candidates = [raw, _CODE_FENCE_RE.sub("", raw).strip()]

        brace_span = StructuredOutputEngine._extract_outer_braces(raw)
        if brace_span:
            candidates.append(brace_span)

        for candidate in candidates:
            parsed = StructuredOutputEngine._try_load(candidate)
            if parsed is not None:
                return parsed
            fixed = _TRAILING_COMMA_RE.sub(r"\1", candidate)
            parsed = StructuredOutputEngine._try_load(fixed)
            if parsed is not None:
                return parsed

        raise StructuredOutputParseError(
            "Could not parse a JSON object out of the model's response.",
            details={"raw_response": raw[:500]},
        )

    @staticmethod
    def _try_load(text: str) -> dict | None:
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            return None
        return result if isinstance(result, dict) else None

    @staticmethod
    def _extract_outer_braces(text: str) -> str | None:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return text[start : end + 1]

    @staticmethod
    def validate_schema(data: dict, schema: type[T]) -> T:
        """Validate `data` against a task-specific Pydantic schema."""
        try:
            return schema.model_validate(data)
        except ValidationError as exc:
            raise StructuredOutputParseError(
                f"Output failed schema validation against {schema.__name__}.",
                details={"errors": exc.errors(include_url=False, include_context=False)},
            ) from exc

    @staticmethod
    def extract_confidence(data: dict, *, default: float = 0.5) -> float:
        """Pull a confidence value out of a raw parsed payload, tolerating
        the common variants agents/models might use for the key."""
        for key in ("confidence", "confidence_score", "score"):
            value = data.get(key)
            if isinstance(value, int | float):
                return max(0.0, min(1.0, float(value)))
        return default

    @classmethod
    def to_structured_output(
        cls, raw: str, *, used_fallback: bool = False, rationale: str | None = None
    ) -> StructuredOutput:
        """Convenience end-to-end path: raw LLM text -> `StructuredOutput`."""
        data = cls.parse_json(raw)
        confidence = cls.extract_confidence(data)
        return StructuredOutput(
            data=data,
            confidence=confidence,
            used_fallback=used_fallback,
            rationale=rationale or data.get("rationale"),
        )
