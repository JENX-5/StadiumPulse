from __future__ import annotations

import pytest

from app.agents.exceptions import AgentValidationError, PromptNotFoundError
from app.agents.prompts import PromptRegistry, PromptTemplate


def test_render_substitutes_variables():
    template = PromptTemplate.create(
        name="incident_summary",
        version=1,
        template="Summarize this incident: {raw_text}",
        required_variables=("raw_text",),
    )
    assert (
        template.render(raw_text="fire near gate 3") == "Summarize this incident: fire near gate 3"
    )


def test_render_missing_variable_raises():
    template = PromptTemplate.create(
        name="incident_summary", version=1, template="{raw_text}", required_variables=("raw_text",)
    )
    with pytest.raises(AgentValidationError):
        template.render()


def test_create_rejects_undeclared_template_field():
    with pytest.raises(AgentValidationError):
        PromptTemplate.create(name="bad", version=1, template="{oops}", required_variables=())


def test_registry_returns_latest_version_by_default():
    registry = PromptRegistry()
    registry.register(PromptTemplate.create(name="p", version=1, template="v1"))
    registry.register(PromptTemplate.create(name="p", version=2, template="v2"))

    assert registry.get("p").version == 2
    assert registry.get("p", version=1).version == 1


def test_registry_unknown_name_raises():
    registry = PromptRegistry()
    with pytest.raises(PromptNotFoundError):
        registry.get("nonexistent")


def test_registry_unknown_version_raises():
    registry = PromptRegistry()
    registry.register(PromptTemplate.create(name="p", version=1, template="v1"))
    with pytest.raises(PromptNotFoundError):
        registry.get("p", version=99)
