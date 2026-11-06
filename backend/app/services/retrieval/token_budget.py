from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable


TokenCounter = Callable[[str], int]
_VALID_BOUNDARY_TYPES = {"scenario", "checkpoint", "catalog_card"}


@dataclass(frozen=True)
class TokenBudgetConfig:
    model_context_limit: int
    system_prompt_tokens: int
    schema_and_tool_tokens: int
    reserved_output_tokens: int
    runtime_margin: int

    @property
    def available_input_tokens(self) -> int:
        values = (
            self.model_context_limit,
            self.system_prompt_tokens,
            self.schema_and_tool_tokens,
            self.reserved_output_tokens,
            self.runtime_margin,
        )
        if any(value < 0 for value in values) or self.model_context_limit <= 0:
            raise ValueError("Token budget values must be nonnegative with a positive model limit.")
        available = (
            self.model_context_limit
            - self.system_prompt_tokens
            - self.schema_and_tool_tokens
            - self.reserved_output_tokens
            - self.runtime_margin
        )
        if available <= 0:
            raise ValueError("Configured fixed context costs leave no input budget.")
        return available


@dataclass(frozen=True)
class ContextUnit:
    """A complete source unit that may be separated from its neighbors."""

    unit_id: str
    boundary_type: str
    content: str


@dataclass(frozen=True)
class ContextBatch:
    units: tuple[ContextUnit, ...]
    content: str
    token_count: int


class ContextBudgetExceeded(ValueError):
    def __init__(self, unit_ids: tuple[str, ...], token_count: int, available: int) -> None:
        self.unit_ids = unit_ids
        self.token_count = token_count
        self.available = available
        super().__init__(
            f"Complete context unit(s) {', '.join(unit_ids)} require "
            f"{token_count} tokens; only {available} are available."
        )


class TokenBudgeter:
    """Measures and packs complete units using the configured model tokenizer."""

    def __init__(self, config: TokenBudgetConfig, token_counter: TokenCounter) -> None:
        if not callable(token_counter):
            raise TypeError("A model-specific token counter is required.")
        self.config = config
        self.token_counter = token_counter

    def count_tokens(self, content: str) -> int:
        count = self.token_counter(content)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("The configured tokenizer must return a nonnegative integer.")
        return count

    def pack(self, units: Iterable[ContextUnit]) -> tuple[ContextBatch, ...]:
        available = self.config.available_input_tokens
        materialized = tuple(units)
        if any(not unit.unit_id or not unit.boundary_type for unit in materialized):
            raise ValueError("Each context unit needs an id and an explicit split boundary type.")
        if any(unit.boundary_type not in _VALID_BOUNDARY_TYPES for unit in materialized):
            raise ValueError(
                "Context units may split only at scenario, checkpoint, or catalog-card boundaries."
            )
        if len({unit.unit_id for unit in materialized}) != len(materialized):
            raise ValueError("Context unit ids must be unique within a packing request.")

        batches: list[ContextBatch] = []
        current: list[ContextUnit] = []
        for unit in materialized:
            proposed = current + [unit]
            content = _join_content(proposed)
            token_count = self.count_tokens(content)
            if token_count <= available:
                current = proposed
                continue
            if current:
                batches.append(_batch(current, self.count_tokens))
            unit_count = self.count_tokens(unit.content)
            if unit_count > available:
                raise ContextBudgetExceeded((unit.unit_id,), unit_count, available)
            current = [unit]

        if current:
            batches.append(_batch(current, self.count_tokens))
        return tuple(batches)


def _join_content(units: Iterable[ContextUnit]) -> str:
    return "\n\n".join(unit.content for unit in units)


def _batch(
    units: list[ContextUnit],
    count_tokens: TokenCounter,
) -> ContextBatch:
    content = _join_content(units)
    token_count = count_tokens(content)
    return ContextBatch(tuple(units), content, token_count)
