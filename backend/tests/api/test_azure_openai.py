"""U13 (`DT-101`): Azure OpenAI adapter, settings and wiring, without network (`CLAUDE.md` §12.5)."""

from __future__ import annotations

import io
import json
import unittest
import urllib.error
import urllib.parse

from test_settings import ENTRA, env

from app.api.app import create_app
from app.api.azure_openai import AzureOpenAIChat, AzureOpenAIConfig, ManagedIdentityToken
from app.api.settings import SettingsError, load_settings
from app.genai import ChatGenerator, GeneratorUnavailable, TemplateGenerator

CONFIG = AzureOpenAIConfig("https://aoai-mpa-dev.openai.azure.com", "gpt-41-mini", "client-id-1",
                           max_calls_per_minute=2)
IDENTITY = {"IDENTITY_ENDPOINT": "http://localhost:42356/msi/token", "IDENTITY_HEADER": "header-value"}
MESSAGES = (("system", "instrucciones"), ("user", "datos"))
AOAI = {"GENAI_PROVIDER": "azure-openai", "AZURE_OPENAI_ENDPOINT": "https://aoai-mpa-dev.openai.azure.com/",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-41-mini", "AZURE_CLIENT_ID": "client-id-1"}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


class FakeOpener:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return FakeResponse(json.dumps(answer).encode() if not isinstance(answer, bytes) else answer)


def completion(text="Se sugiere pedir 2700 BOX.", finish="stop"):
    return {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}]}


class TokenTest(unittest.TestCase):
    def test_request_and_cache_until_the_refresh_margin(self) -> None:
        opener = FakeOpener({"access_token": "tok-1", "expires_on": "4000"}, {"access_token": "tok-2", "expires_on": "9000"})
        now = [1000.0]
        token = ManagedIdentityToken(CONFIG, IDENTITY, opener, lambda: now[0])
        self.assertEqual(token.get(), "tok-1")
        request, timeout = opener.requests[0]
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
        self.assertEqual(query, {"resource": ["https://cognitiveservices.azure.com"], "api-version": ["2019-08-01"],
                                 "client_id": ["client-id-1"]})
        self.assertEqual(request.get_header("X-identity-header"), "header-value")
        self.assertEqual(timeout, CONFIG.timeout_seconds)
        now[0] = 3600.0  # 400 s before expiry: still valid
        self.assertEqual(token.get(), "tok-1")
        now[0] = 3800.0  # inside the 300 s margin: refreshed
        self.assertEqual(token.get(), "tok-2")
        self.assertEqual(len(opener.requests), 2)

    def test_failures_are_unavailable_without_secrets(self) -> None:
        cases = {
            "no endpoint": ({}, FakeOpener()),
            "HTTP 400": (IDENTITY, FakeOpener(urllib.error.HTTPError("u", 400, "bad", {}, None))),
            "network": (IDENTITY, FakeOpener(urllib.error.URLError("down"))),
            "no token": (IDENTITY, FakeOpener({"expires_on": "9"})),
            "bad JSON": (IDENTITY, FakeOpener(b"<html>")),
        }
        for name, (environ, opener) in cases.items():
            with self.subTest(name), self.assertRaises(GeneratorUnavailable) as caught:
                ManagedIdentityToken(CONFIG, environ, opener).get()
            self.assertNotIn("header-value", str(caught.exception))


class ChatTest(unittest.TestCase):
    def test_request_shape(self) -> None:
        opener = FakeOpener(completion())
        chat = AzureOpenAIChat(CONFIG, lambda: "tok-1", opener)
        self.assertEqual(chat(MESSAGES), "Se sugiere pedir 2700 BOX.")
        request, timeout = opener.requests[0]
        self.assertEqual(request.full_url, "https://aoai-mpa-dev.openai.azure.com/openai/v1/chat/completions")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer tok-1")
        self.assertNotIn("api-version", request.full_url)
        body = json.loads(request.data)
        self.assertEqual(body["model"], "gpt-41-mini")
        self.assertEqual(body["messages"], [{"role": "system", "content": "instrucciones"},
                                            {"role": "user", "content": "datos"}])
        self.assertEqual((body["temperature"], body["max_tokens"]), (0.2, 400))
        self.assertNotIn("tools", body)
        self.assertEqual(timeout, CONFIG.timeout_seconds)

    def test_identical_prompts_are_cached(self) -> None:
        opener = FakeOpener(completion())
        chat = AzureOpenAIChat(CONFIG, lambda: "tok-1", opener)
        self.assertEqual(chat(MESSAGES), chat(MESSAGES))
        self.assertEqual(len(opener.requests), 1)

    def test_rate_limit_per_minute(self) -> None:
        now = [0.0]
        opener = FakeOpener(completion("a"), completion("b"), completion("c"))
        chat = AzureOpenAIChat(CONFIG, lambda: "tok", opener, lambda: now[0])
        chat((("user", "1"),))
        chat((("user", "2"),))
        with self.assertRaises(GeneratorUnavailable):
            chat((("user", "3"),))
        now[0] = 61.0
        self.assertEqual(chat((("user", "3"),)), "c")

    def test_bad_answers_are_unavailable(self) -> None:
        cases = {
            "HTTP 429": urllib.error.HTTPError("u", 429, "too many", {}, None),
            "timeout": TimeoutError(),
            "no choices": {"choices": []},
            "truncated": completion(finish="length"),
            "filtered": completion(finish="content_filter"),
            "empty": completion(text="  "),
        }
        for name, answer in cases.items():
            with self.subTest(name), self.assertRaises(GeneratorUnavailable):
                AzureOpenAIChat(CONFIG, lambda: "tok", FakeOpener(answer))(MESSAGES)


class SettingsTest(unittest.TestCase):
    def dev(self, **overrides):
        return env(APP_ENV="dev", DEV_AUTH_IDENTITIES=None, **ENTRA, **{**AOAI, **overrides})

    def test_template_is_the_default(self) -> None:
        self.assertIsNone(load_settings(env()).genai)
        self.assertIsNone(load_settings(env(APP_ENV="dev", DEV_AUTH_IDENTITIES=None, **ENTRA)).genai)

    def test_azure_openai_in_dev(self) -> None:
        genai = load_settings(self.dev(GENAI_TIMEOUT_SECONDS="5")).genai
        self.assertEqual((genai.endpoint, genai.deployment, genai.client_id, genai.timeout_seconds),
                         ("https://aoai-mpa-dev.openai.azure.com", "gpt-41-mini", "client-id-1", 5.0))

    def test_refusals(self) -> None:
        cases = {
            "local": env(**AOAI),
            "unknown provider": self.dev(GENAI_PROVIDER="openai"),
            "missing deployment": self.dev(AZURE_OPENAI_DEPLOYMENT=None),
            "missing client id": self.dev(AZURE_CLIENT_ID=None),
            "http endpoint": self.dev(AZURE_OPENAI_ENDPOINT="http://aoai-mpa-dev.openai.azure.com"),
            "foreign host": self.dev(AZURE_OPENAI_ENDPOINT="https://example.com"),
            "path in endpoint": self.dev(AZURE_OPENAI_ENDPOINT="https://a.openai.azure.com/openai/v1"),
            "a key": self.dev(AZURE_OPENAI_API_KEY="k"),
            "timeout out of range": self.dev(GENAI_TIMEOUT_SECONDS="60"),
            "calls not a number": self.dev(GENAI_MAX_CALLS_PER_MINUTE="many"),
        }
        for name, environ in cases.items():
            with self.subTest(name), self.assertRaises(SettingsError) as caught:
                load_settings(environ)
            self.assertNotIn("k\"", str(caught.exception))


class WiringTest(unittest.TestCase):
    def test_template_only_by_default(self) -> None:
        from _api_support import settings

        app = create_app(settings())
        self.assertIsInstance(app.state.text_generator, TemplateGenerator)
        self.assertIsNone(app.state.text_fallback)

    def test_azure_openai_with_template_fallback(self) -> None:
        loaded = load_settings(TestEnv.dev())
        app = create_app(loaded, validator=object())
        self.assertIsInstance(app.state.text_generator, ChatGenerator)
        self.assertEqual(app.state.text_generator.name, "azure-openai/gpt-41-mini")
        self.assertIsInstance(app.state.text_fallback, TemplateGenerator)


class TestEnv:
    @staticmethod
    def dev():
        return env(APP_ENV="dev", DEV_AUTH_IDENTITIES=None, **ENTRA, **AOAI)


if __name__ == "__main__":
    unittest.main()
