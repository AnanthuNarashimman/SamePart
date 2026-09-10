"""A model running inside the network.

Speaks to an OpenAI-compatible endpoint on the local machine, which is what Ollama, vLLM,
llama.cpp and LM Studio all expose. Nothing here touches the egress guard, because nothing
here leaves the host.

This is the deployment a CPSE would actually run. The hosted path exists so the pipeline can
be developed without a GPU, not because it is the intended shape of the system.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from samepart.model.client import ModelReply

DEFAULT_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "qwen2.5:7b-instruct"


def local_url() -> str:
    return os.getenv("SAMEPART_LOCAL_MODEL_URL", "").strip() or DEFAULT_URL


def local_model_name() -> str:
    return os.getenv("SAMEPART_LOCAL_MODEL", "").strip() or DEFAULT_MODEL


def local_configured() -> bool:
    """Only claim a local model when one has been asked for explicitly."""
    return bool(os.getenv("SAMEPART_LOCAL_MODEL") or os.getenv("SAMEPART_LOCAL_MODEL_URL"))


def _is_loopback(url: str) -> bool:
    return any(h in url for h in ("localhost", "127.0.0.1", "::1", "0.0.0.0"))


class LocalModel:
    def __init__(self) -> None:
        self.url = local_url().rstrip("/")
        self.name = local_model_name()
        self.on_host = _is_loopback(self.url)
        self.available = self._reachable()

    def _reachable(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.url}/models", timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def json(self, system: str, user: str, max_tokens: int = 1200) -> ModelReply:
        started = time.time()
        body = json.dumps({
            "model": self.name,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }).encode()

        request = urllib.request.Request(
            f"{self.url}/chat/completions", data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = json.loads(response.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return ModelReply({}, False, error=f"local model unreachable: {exc}",
                              latency_ms=int((time.time() - started) * 1000))

        text = (payload.get("choices", [{}])[0]
                .get("message", {}).get("content", "") or "").strip()
        usage = payload.get("usage", {}) or {}
        reply = ModelReply({}, False, raw=text,
                           latency_ms=int((time.time() - started) * 1000),
                           tokens_in=usage.get("prompt_tokens", 0) or 0,
                           tokens_out=usage.get("completion_tokens", 0) or 0)
        try:
            reply.data = json.loads(text)
            reply.ok = isinstance(reply.data, dict)
        except json.JSONDecodeError as exc:
            reply.error = f"local model did not return JSON: {exc}"
        return reply
