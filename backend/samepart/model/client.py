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
from samepart.model.egress import EgressBlocked, guard


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
        self._host = (settings.azure_endpoint or "azure").replace("https://", "").rstrip("/")
        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_endpoint,
            api_key=settings.azure_api_key,
            api_version=settings.azure_api_version,
        )

    def json(self, system: str, user: str, max_tokens: int = 1200) -> ModelReply:
        started = time.time()

        # Nothing reaches the network before the guard has seen it. A blocked call still
        # leaves a full record of what would have gone.
        try:
            guard(self._host, "model inference", f"{system}\n\n{user}")
        except EgressBlocked as blocked:
            return ModelReply({}, False, error=str(blocked),
                              latency_ms=int((time.time() - started) * 1000))

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
    """Local first, always.

    A local model needs no egress at all, so where one is configured it is preferred over a
    hosted endpoint regardless of what else is available. That ordering is the policy: the
    hosted path is the fallback, not the default.
    """
    from samepart.model.local import LocalModel, local_configured

    if local_configured():
        model = LocalModel()
        if model.available:
            return model
    return AzureModel() if settings.has_azure else NullModel()
