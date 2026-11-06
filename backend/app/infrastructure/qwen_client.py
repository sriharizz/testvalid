from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


class QwenConfigurationError(ValueError):
    pass


class QwenClientError(RuntimeError):
    """Sanitized model transport/response error. Never includes request or secret data."""


@dataclass(frozen=True)
class QwenSettings:
    provider: str
    base_url: str
    api_key: str
    model_name: str
    timeout_seconds: float = 60.0
    max_completion_tokens: int = 8192
    json_schema_mode: bool = False

    @classmethod
    def from_environment(cls) -> QwenSettings:
        provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
        if provider == "groq":
            base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
            api_key = os.getenv("GROQ_API_KEY", "")
            model_name = os.getenv("GROQ_MODEL", "")
        elif provider in {"qwen", "openai_compatible"}:
            base_url = os.getenv("QWEN_BASE_URL", "")
            api_key = os.getenv("QWEN_API_KEY", "")
            model_name = os.getenv("QWEN_MODEL_NAME", "")
        else:
            raise QwenConfigurationError("LLM_PROVIDER must be groq or openai_compatible.")

        if not base_url.strip() or not model_name.strip():
            raise QwenConfigurationError("Model base URL and model name are required.")
        if not api_key.strip() and provider != "openai_compatible":
            raise QwenConfigurationError("A provider API key is required.")
        try:
            timeout = float(os.getenv("PLANNER_TIMEOUT_SECONDS", "60"))
            max_tokens = int(os.getenv("PLANNER_MAX_COMPLETION_TOKENS", "8192"))
        except ValueError as exc:
            raise QwenConfigurationError("Planner timeout/token settings are invalid.") from exc
        if timeout <= 0 or max_tokens <= 0:
            raise QwenConfigurationError("Planner timeout/token settings must be positive.")
        return cls(
            provider=provider,
            base_url=base_url.strip().rstrip("/"),
            api_key=api_key.strip(),
            model_name=model_name.strip(),
            timeout_seconds=timeout,
            max_completion_tokens=max_tokens,
            json_schema_mode=os.getenv("PLANNER_JSON_SCHEMA_MODE", "0").strip() == "1",
        )


@dataclass(frozen=True)
class QwenCompletion:
    content: str
    model_name: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


class QwenClient:
    """OpenAI-compatible chat adapter for a configured Qwen model provider."""

    def __init__(
        self,
        settings: QwenSettings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self._client = httpx.Client(
            timeout=settings.timeout_seconds,
            transport=transport,
            follow_redirects=False,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> QwenClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        repair_feedback: str | None = None,
    ) -> QwenCompletion:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        if repair_feedback:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your prior response failed deterministic validation. Return a corrected "
                        "JSON object matching the same schema. Preserve all source references. "
                        f"Validation issues: {repair_feedback}"
                    ),
                }
            )

        payload: dict[str, Any] = {
            "model": self.settings.model_name,
            "messages": messages,
            "temperature": 0,
            "max_completion_tokens": self.settings.max_completion_tokens,
            "response_format": {"type": "json_object"},
        }
        if self.settings.json_schema_mode:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "data_generation_output",
                    "strict": True,
                    "schema": schema,
                },
            }

        headers = {"Accept": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        url = f"{self.settings.base_url}/chat/completions"
        try:
            response = self._client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            suffix = f" (HTTP {status})" if status is not None else ""
            raise QwenClientError(f"Model request failed{suffix}; response details were redacted.") from None

        try:
            content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise TypeError("empty model content")
            usage = body.get("usage") or {}
            return QwenCompletion(
                content=content,
                model_name=str(body.get("model") or self.settings.model_name),
                prompt_tokens=_optional_count(usage.get("prompt_tokens")),
                completion_tokens=_optional_count(usage.get("completion_tokens")),
                total_tokens=_optional_count(usage.get("total_tokens")),
            )
        except (KeyError, IndexError, TypeError, AttributeError):
            raise QwenClientError("Model response did not match the expected chat-completion shape.") from None


def _optional_count(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value
