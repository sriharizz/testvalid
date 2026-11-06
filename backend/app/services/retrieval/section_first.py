from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from backend.app.services.retrieval.ui_mini_rag import RetrievalResult, RetrievalScope, UIMiniRAG


@dataclass(frozen=True)
class SectionContext:
    retrieval: RetrievalResult
    selected_section_paths: tuple[tuple[str, ...], ...]
    selection_mode: str


class SectionFirstRetriever:
    """Resolve named sections first; otherwise retrieve a bounded control set."""

    def __init__(
        self,
        mini_rag: UIMiniRAG,
        *,
        fallback_top_k: int = 5,
        option_candidate_limit: int = 10,
    ) -> None:
        if fallback_top_k < 1:
            raise ValueError("fallback_top_k must be positive.")
        if option_candidate_limit < 1:
            raise ValueError("option_candidate_limit must be positive.")
        self.mini_rag = mini_rag
        self.fallback_top_k = fallback_top_k
        self.option_candidate_limit = option_candidate_limit

    def retrieve(self, query: str, scope: RetrievalScope) -> SectionContext:
        query_text = query.strip()
        if not query_text:
            return SectionContext(
                self.mini_rag.retrieve(query_text, scope, top_k=self.fallback_top_k),
                (),
                "no_query",
            )
        ranked = self.mini_rag.retrieve(
            query_text,
            scope,
            top_k=max(1, len(self.mini_rag.records)),
        )
        if ranked.status != "retrieved":
            return SectionContext(ranked, (), "fallback")
        paths = _explicit_section_paths(query_text, ranked.records)
        if paths:
            expanded = self.mini_rag.retrieve_sections(
                paths,
                scope,
                option_candidate_limit=self.option_candidate_limit,
            )
            mode = "section_expansion" if expanded.status == "retrieved" else "section_needs_review"
            return SectionContext(expanded, paths, mode)
        fallback = self.mini_rag.retrieve(query_text, scope, top_k=self.fallback_top_k)
        return SectionContext(fallback, (), "ranked_controls")


def _explicit_section_paths(query: str, ranked_records) -> tuple[tuple[str, ...], ...]:
    normalized_query = _normalize(query)
    query_words = set(normalized_query.split())
    by_path: dict[tuple[str, ...], object] = {}
    matched_labels: set[str] = set()
    for item in ranked_records:
        record = item.record
        if record.record_type != "section" or not record.section_path:
            continue
        label = _normalize(record.label)
        label_words = label.split()
        phrase_match = bool(label and f" {label} " in f" {normalized_query} ")
        word_match = bool(label_words) and all(
            any(_word_match(label_word, query_word) for query_word in query_words)
            for label_word in label_words
        )
        if phrase_match or word_match:
            by_path[tuple(record.section_path)] = item
            matched_labels.add(label)

    # A section card may fall below the lexical rank threshold even when one
    # of its controls is relevant. Use that already-retrieved control's path
    # as a generic fallback for partially matching multiword section labels.
    # Exact section matches above remain primary; unrelated sibling sections
    # are not expanded unless a relevant control provides evidence for them.
    for item in ranked_records:
        record = item.record
        if record.record_type != "control" or not record.section_path:
            continue
        label = _normalize(record.section_path[-1])
        if label in matched_labels or not _partial_section_match(label, query_words):
            continue
        by_path.setdefault(tuple(record.section_path), item)
        matched_labels.add(label)

    selected: list[tuple[str, ...]] = []
    labels: set[str] = set()
    for path, item in sorted(
        by_path.items(),
        key=lambda entry: (len(entry[0]), tuple(part.casefold() for part in entry[0])),
    ):
        label = _normalize(path[-1])
        if label in labels:
            continue
        selected.append(path)
        labels.add(label)
    return tuple(selected)


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[^\W_]+", text.casefold(), flags=re.UNICODE))


def _word_match(label_word: str, query_word: str) -> bool:
    if label_word == query_word:
        return True
    if min(len(label_word), len(query_word)) >= 4 and (
        label_word.startswith(query_word) or query_word.startswith(label_word)
    ):
        return True
    return SequenceMatcher(None, label_word, query_word).ratio() >= 0.86


def _partial_section_match(label: str, query_words: set[str]) -> bool:
    label_words = label.split()
    if len(label_words) < 2:
        return False
    matched = sum(
        any(_word_match(label_word, query_word) for query_word in query_words)
        for label_word in label_words
    )
    return matched / len(label_words) >= 0.5
