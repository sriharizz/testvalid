from __future__ import annotations

from pydantic import ConfigDict, Field

from backend.app.domain.protocol import StrictModel


class AuthoredStepInput(StrictModel):
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    step_id: str | None = None
    procedure: str | None = None
    expected_result: str | None = None


class AuthoredTestCaseInput(StrictModel):
    """Structured authoring payload; prose fields stay verbatim and uninterpreted."""

    model_config = ConfigDict(extra="allow", validate_assignment=True)

    test_set_id: str | None = None
    test_set_title: str | None = None
    test_case_id: str | None = None
    title: str | None = None
    procedure: str | None = None
    expected_result: str | None = None
    steps: list[AuthoredStepInput] = Field(default_factory=list)

