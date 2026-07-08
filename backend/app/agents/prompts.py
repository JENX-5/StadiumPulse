"""
Prompt management.

Centralizes prompt *templates* (with variable substitution and versioning)
separately from each agent's `system_prompt` string — an agent's
system_prompt is fixed identity/role text, while `PromptTemplate` is for
the per-call user-prompt text that varies with task input and needs to be
tweakable/versioned without touching agent code.
"""

from __future__ import annotations

import string
from dataclasses import dataclass, field

from app.agents.exceptions import AgentValidationError, PromptNotFoundError


@dataclass(slots=True, frozen=True)
class PromptTemplate:
    """One versioned prompt template.

    Uses `string.Template`-style `$variable` substitution (via
    `string.Formatter`'s field-name extraction for validation, then
    `str.format_map` for rendering) rather than raw f-strings, so
    templates can be stored as plain data (e.g. loaded from a file or DB
    later) instead of Python code.
    """

    name: str
    version: int
    template: str
    required_variables: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""

    def render(self, **variables: object) -> str:
        missing = [v for v in self.required_variables if v not in variables]
        if missing:
            raise AgentValidationError(
                f"Prompt '{self.name}' v{self.version} is missing required variables: {missing}"
            )
        try:
            return self.template.format(**variables)
        except KeyError as exc:
            raise AgentValidationError(
                f"Prompt '{self.name}' v{self.version} references undefined variable: {exc}"
            ) from exc

    @classmethod
    def create(
        cls,
        *,
        name: str,
        version: int,
        template: str,
        required_variables: tuple[str, ...] = (),
        description: str = "",
    ) -> PromptTemplate:
        """Validate at creation time that every declared required variable
        actually appears as a format field in `template`, and vice versa,
        so a typo doesn't surface only when the template is first rendered
        against live input."""
        field_names = {name for _, name, _, _ in string.Formatter().parse(template) if name}
        declared = set(required_variables)
        undeclared_fields = field_names - declared
        if undeclared_fields:
            raise AgentValidationError(
                f"Prompt '{name}' v{version} uses undeclared template fields: {undeclared_fields}"
            )
        return cls(
            name=name,
            version=version,
            template=template,
            required_variables=required_variables,
            description=description,
        )


class PromptRegistry:
    """Stores every registered `PromptTemplate`, keyed by name -> version."""

    def __init__(self) -> None:
        self._templates: dict[str, dict[int, PromptTemplate]] = {}

    def register(self, template: PromptTemplate) -> None:
        versions = self._templates.setdefault(template.name, {})
        versions[template.version] = template

    def get(self, name: str, *, version: int | None = None) -> PromptTemplate:
        """Return a specific version, or the latest registered version if
        `version` is omitted."""
        versions = self._templates.get(name)
        if not versions:
            raise PromptNotFoundError(f"No prompt template registered with name '{name}'")
        if version is None:
            version = max(versions)
        template = versions.get(version)
        if template is None:
            raise PromptNotFoundError(
                f"Prompt '{name}' has no version {version}",
                details={"available_versions": sorted(versions)},
            )
        return template

    def list_names(self) -> list[str]:
        return list(self._templates.keys())

    def list_versions(self, name: str) -> list[int]:
        return sorted(self._templates.get(name, {}))
