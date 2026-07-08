from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.agents.exceptions import StructuredOutputParseError
from app.agents.output import StructuredOutputEngine


def test_parses_clean_json():
    result = StructuredOutputEngine.parse_json('{"a": 1, "b": "x"}')
    assert result == {"a": 1, "b": "x"}


def test_recovers_from_markdown_code_fence():
    raw = '```json\n{"a": 1}\n```'
    assert StructuredOutputEngine.parse_json(raw) == {"a": 1}


def test_recovers_from_surrounding_prose():
    raw = 'Sure, here is the JSON:\n{"a": 1}\nHope that helps!'
    assert StructuredOutputEngine.parse_json(raw) == {"a": 1}


def test_recovers_from_trailing_comma():
    raw = '{"a": 1, "b": 2,}'
    assert StructuredOutputEngine.parse_json(raw) == {"a": 1, "b": 2}


def test_unparseable_text_raises():
    with pytest.raises(StructuredOutputParseError):
        StructuredOutputEngine.parse_json("this is not json at all")


def test_extract_confidence_variants():
    assert StructuredOutputEngine.extract_confidence({"confidence": 0.7}) == 0.7
    assert StructuredOutputEngine.extract_confidence({"score": 1.5}) == 1.0  # clamped
    assert StructuredOutputEngine.extract_confidence({}) == 0.5  # default


class _Schema(BaseModel):
    action: str
    priority: int


def test_validate_schema_success():
    result = StructuredOutputEngine.validate_schema({"action": "dispatch", "priority": 1}, _Schema)
    assert result.action == "dispatch"


def test_validate_schema_failure_raises_structured_error():
    with pytest.raises(StructuredOutputParseError):
        StructuredOutputEngine.validate_schema({"action": "dispatch"}, _Schema)


def test_to_structured_output_end_to_end():
    output = StructuredOutputEngine.to_structured_output('{"confidence": 0.8, "action": "x"}')
    assert output.confidence == 0.8
    assert output.data["action"] == "x"
