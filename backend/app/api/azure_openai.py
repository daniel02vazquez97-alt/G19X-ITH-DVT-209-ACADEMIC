"""U13 (`DT-101`): HTTP adapter to Azure OpenAI with the managed identity, standard library only.

* Token: the Container Apps identity endpoint (``IDENTITY_ENDPOINT`` + header ``X-IDENTITY-HEADER``,
  ``api-version=2019-08-01``, ``client_id`` of the user-assigned identity ``id-mpa-dev-runtime``). No key: the
  account has ``disableLocalAuth`` and the identity holds *Cognitive Services OpenAI User* on it.
* Call: ``POST {endpoint}/openai/v1/chat/completions`` (v1 API, no ``api-version``), ``model`` = deployment.
* Limits (`docs/09` §9): short timeout, a global cap of calls per minute and a small cache of identical prompts.
  Every failure is ``GeneratorUnavailable``: ``explain`` falls back to the template and the API answers 200.

Messages and errors never contain the token, the prompt or the answer.
"""

from __future__ import annotations

import collections
import hashlib
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from app.genai import GeneratorUnavailable, message_list

IDENTITY_API_VERSION = "2019-08-01"
TOKEN_REFRESH_MARGIN = 300  # seconds before expires_on
CACHE_SIZE = 256

Opener = Callable[..., Any]  # urllib.request.urlopen-compatible: (request, timeout=...) -> response


@dataclass(frozen=True)
class AzureOpenAIConfig:
    endpoint: str  # https://<account>.openai.azure.com
    deployment: str
    client_id: str  # client id of the user-assigned identity
    token_resource: str = "https://cognitiveservices.azure.com"
    timeout_seconds: float = 10.0
    max_calls_per_minute: int = 30
    max_tokens: int = 400
    temperature: float = 0.2


class ManagedIdentityToken:
    """Cached access token of the user-assigned identity; refreshed ``TOKEN_REFRESH_MARGIN`` s before expiry."""

    def __init__(self, config: AzureOpenAIConfig, environ: Mapping[str, str], opener: Opener = urllib.request.urlopen,
                 clock: Callable[[], float] = time.time) -> None:
        self._config = config
        self._environ = environ
        self._opener = opener
        self._clock = clock
        self._lock = threading.Lock()
        self._token: str | None = None
        self._expires_on = 0.0

    def get(self) -> str:
        with self._lock:
            if self._token is None or self._clock() >= self._expires_on - TOKEN_REFRESH_MARGIN:
                self._token, self._expires_on = self._fetch()
            return self._token

    def _fetch(self) -> tuple[str, float]:
        endpoint = self._environ.get("IDENTITY_ENDPOINT")
        header = self._environ.get("IDENTITY_HEADER")
        if not endpoint or not header:
            raise GeneratorUnavailable("no managed identity endpoint")
        query = urllib.parse.urlencode({"resource": self._config.token_resource, "api-version": IDENTITY_API_VERSION,
                                        "client_id": self._config.client_id})
        request = urllib.request.Request(f"{endpoint}?{query}", headers={"X-IDENTITY-HEADER": header}, method="GET")
        body = _read_json(self._opener, request, self._config.timeout_seconds, "identity")
        token = body.get("access_token") if isinstance(body, dict) else None
        try:
            expires_on = float(body.get("expires_on"))
        except (TypeError, ValueError):
            expires_on = 0.0
        if not isinstance(token, str) or not token or expires_on <= 0:
            raise GeneratorUnavailable("identity: unexpected token answer")
        return token, expires_on


class AzureOpenAIChat:
    """``complete(messages) -> text``: the injected call of ``app.genai.ChatGenerator``."""

    def __init__(self, config: AzureOpenAIConfig, token: Callable[[], str], opener: Opener = urllib.request.urlopen,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._config = config
        self._token = token
        self._opener = opener
        self._clock = clock
        self._lock = threading.Lock()
        self._calls: collections.deque[float] = collections.deque()
        self._cache: collections.OrderedDict[str, str] = collections.OrderedDict()
        self.url = config.endpoint.rstrip("/") + "/openai/v1/chat/completions"

    def __call__(self, messages: tuple[tuple[str, str], ...]) -> str:
        key = hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode("utf-8")).hexdigest()
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            self._take_slot()
        payload = {
            "model": self._config.deployment,
            "messages": message_list(messages),
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
        }
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"},
            method="POST",
        )
        body = _read_json(self._opener, request, self._config.timeout_seconds, "chat")
        try:
            choice = body["choices"][0]
            text = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GeneratorUnavailable("chat: unexpected answer") from exc
        if choice.get("finish_reason") not in (None, "stop"):
            raise GeneratorUnavailable(f"chat: finish_reason {choice.get('finish_reason')}")
        if not isinstance(text, str) or not text.strip():
            raise GeneratorUnavailable("chat: empty answer")
        with self._lock:
            self._cache[key] = text
            while len(self._cache) > CACHE_SIZE:
                self._cache.popitem(last=False)
        return text

    def _take_slot(self) -> None:
        now = self._clock()
        while self._calls and now - self._calls[0] >= 60:
            self._calls.popleft()
        if len(self._calls) >= self._config.max_calls_per_minute:
            raise GeneratorUnavailable("rate limit")
        self._calls.append(now)


def _read_json(opener: Opener, request: urllib.request.Request, timeout: float, what: str) -> Any:
    try:
        with opener(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise GeneratorUnavailable(f"{what}: HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise GeneratorUnavailable(f"{what}: {type(exc).__name__}") from None
    try:
        return json.loads(raw)
    except ValueError:
        raise GeneratorUnavailable(f"{what}: invalid JSON") from None
