"""Model access, behind one interface.

Everything that calls a model goes through here, so swapping a hosted deployment for an
open-weight model running inside a CPSE's own network is a configuration change rather than
a rewrite. That is what makes the on-premises claim real instead of aspirational.

When nothing is configured, `NullModel` is returned and every caller degrades to the
deterministic path. The pipeline never depends on a model being available, which is also why
the demo cannot be broken by an API outage.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

from samepart.config import settings


@dataclass
class ModelReply:
    data: dict[str, Any]
    ok: bool
    raw: str = ""
    error: str = ""
    latency_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0


class Model(Protocol):
    name: str
    available: bool

    def json(self, system: str, user: str, max_tokens: int = 1200) -> ModelReply: ...


class NullModel:
    """No model configured. Callers fall back to deterministic behaviour."""
    name = "none"
    available = False

    def json(self, system: str, user: str, max_tokens: int = 1200) -> ModelReply:
        return ModelReply({}, False, error="no model configured")


class AzureModel:
    def __init__(self) -> None:
        from openai import AzureOpenAI

        self.name = settings.azure_chat_deployment or "azure"
        self.available = True
        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_endpoint,
            api_key=settings.azure_api_key,
            api_version=settings.azure_api_version,
        )

    def json(self, system: str, user: str, max_tokens: int = 1200) -> ModelReply:
        started = time.time()
        try:
            resp = self._client.chat.completions.create(
                model=settings.azure_chat_deployment,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                max_completion_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except Exception as exc:                      # network, auth, quota, bad deployment
            return ModelReply({}, False, error=f"{type(exc).__name__}: {exc}",
                              latency_ms=int((time.time() - started) * 1000))

        text = (resp.choices[0].message.content or "").strip()
        usage = getattr(resp, "usage", None)
        reply = ModelReply(
            {}, False, raw=text, latency_ms=int((time.time() - started) * 1000),
            tokens_in=getattr(usage, "prompt_tokens", 0) or 0,
            tokens_out=getattr(usage, "completion_tokens", 0) or 0)
        try:
            reply.data = json.loads(text)
            reply.ok = isinstance(reply.data, dict)
        except json.JSONDecodeError as exc:
            reply.error = f"model did not return JSON: {exc}"
        return reply


def get_model() -> Model:
    return AzureModel() if settings.has_azure else NullModel()
