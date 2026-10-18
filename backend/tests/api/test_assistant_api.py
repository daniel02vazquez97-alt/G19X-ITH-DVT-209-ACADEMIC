"""U15b (`DT-103`): ``GET /api/v1/assistant/answer`` and the ``SEARCH_PROVIDER`` settings, without network."""

from __future__ import annotations

import unittest
from datetime import date

from _api_support import ALL4, TOKENS, auth, client, settings

from app.api.app import create_app
from app.api.assistant import (
    LOCAL_FALLBACK,
    Assistant,
    AssistantUnavailable,
    AzureSearchSettings,
    build_assistant,
    local_retriever,
)
from app.api.settings import Settings, SettingsError, _search_config
from starlette.testclient import TestClient

QUESTION = "¿El asistente puede decidir qué comprar?"
PATH = "/api/v1/assistant/answer"
DEV_SEARCH = {
    "SEARCH_PROVIDER": "azure",
    "AZURE_SEARCH_ENDPOINT": "https://motor-predictivo-search-dev.search.windows.net",
    "AZURE_SEARCH_INDEX": "u15-demo-documents",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "text-embedding-3-small",
    "AZURE_OPENAI_ENDPOINT": "https://oai-mpa-dev-x.openai.azure.com",
    "AZURE_CLIENT_ID": "d920d9fa-0000-4000-8000-000000000003",
}


class Failing:
    def search(self, *_args):
        raise RuntimeError("Azure AI Search HTTP 503")


class EndpointTest(unittest.TestCase):
    def test_the_four_roles_get_an_answer_with_citations_from_the_local_corpus(self) -> None:
        api = client()
        for role in ALL4:
            with self.subTest(role=role):
                response = api.get(PATH, params={"q": QUESTION}, headers=auth(role))
                self.assertEqual(response.status_code, 200, response.text)
                body = response.json()
                self.assertEqual(body["status"], "RETRIEVAL_ONLY")  # local settings: no model
                self.assertEqual((body["retriever"], body["generator"]), ("local", None))
                self.assertEqual((body["data_origin"], body["notices"]), ("SYNTHETIC", ["SYNTHETIC_DATA"]))
                self.assertTrue(body["citations"])
                first = body["citations"][0]
                self.assertEqual(first["number"], 1)
                self.assertTrue(first["source_url"].startswith("knowledge/search_corpus/"))
                self.assertNotIn("security_groups", first)

    def test_authentication_and_question_validation(self) -> None:
        api = client()
        self.assertEqual(api.get(PATH, params={"q": QUESTION}).status_code, 401)
        self.assertEqual(api.get(PATH, params={"q": "no"}, headers=auth("VIEWER")).status_code, 422)
        self.assertEqual(api.get(PATH, params={"q": "x" * 301}, headers=auth("VIEWER")).status_code, 422)
        self.assertEqual(api.get(PATH, headers=auth("VIEWER")).status_code, 422)
        blank = api.get(PATH, params={"q": "   \t  "}, headers=auth("VIEWER"))
        self.assertEqual((blank.status_code, blank.json()["error"]["code"]), (422, "INVALID_QUESTION"))

    def test_without_any_retriever_the_endpoint_answers_503(self) -> None:
        app = create_app(settings())
        app.state.assistant = None
        response = TestClient(app).get(PATH, params={"q": QUESTION}, headers=auth("PLANNER"))
        self.assertEqual((response.status_code, response.json()["error"]["code"]), (503, "ASSISTANT_UNAVAILABLE"))

    def test_the_answer_never_contains_the_token(self) -> None:
        response = client().get(PATH, params={"q": QUESTION}, headers=auth("ADMIN"))
        self.assertNotIn(TOKENS["ADMIN"], response.text)


class AssistantAssemblyTest(unittest.TestCase):
    def test_a_failing_remote_retriever_falls_back_to_the_local_corpus(self) -> None:
        assistant = Assistant(Failing(), "azure-ai-search", local_retriever(), None, None)
        answer = assistant.ask(QUESTION, frozenset({"VIEWER"}), date(2026, 10, 17))
        self.assertEqual(answer.retriever, LOCAL_FALLBACK)
        self.assertTrue(answer.citations)

    def test_without_fallback_the_failure_is_unavailable(self) -> None:
        assistant = Assistant(Failing(), "azure-ai-search", None, None, None)
        with self.assertRaises(AssistantUnavailable):
            assistant.ask(QUESTION, frozenset({"VIEWER"}), date(2026, 10, 17))

    def test_unknown_roles_get_no_groups_and_no_documents(self) -> None:
        assistant = Assistant(None, "local", local_retriever(), None, None)
        self.assertEqual(assistant.ask(QUESTION, frozenset({"GUEST"}), date(2026, 10, 17)).status, "NO_DOCUMENTS")

    def test_local_settings_build_the_local_assistant_and_none_without_corpus(self) -> None:
        self.assertIsNotNone(build_assistant(settings(), None, None))
        self.assertIsNone(build_assistant(settings(), None, None, local=lambda: None))

    def test_azure_settings_build_the_search_retriever_with_the_managed_identity(self) -> None:
        config = AzureSearchSettings(DEV_SEARCH["AZURE_SEARCH_ENDPOINT"], "u15-demo-documents",
                                     DEV_SEARCH["AZURE_OPENAI_ENDPOINT"], "text-embedding-3-small",
                                     DEV_SEARCH["AZURE_CLIENT_ID"])
        fake = Settings("local", "postgresql://x", {})
        object.__setattr__(fake, "search", config)  # bypass the dev-only rule to build without Entra ID
        assistant = build_assistant(fake, None, None, environ={})
        self.assertEqual(type(assistant._primary).__name__, "AzureSearchRetriever")
        # No IDENTITY_ENDPOINT here: the managed identity is unavailable, so the local corpus answers.
        answer = assistant.ask(QUESTION, frozenset({"VIEWER"}), date(2026, 10, 17))
        self.assertEqual(answer.retriever, LOCAL_FALLBACK)


class SearchSettingsTest(unittest.TestCase):
    def test_local_is_the_default(self) -> None:
        self.assertIsNone(_search_config({}, "local"))
        self.assertIsNone(_search_config({"SEARCH_PROVIDER": "local"}, "dev"))

    def test_azure_needs_dev_every_identifier_and_no_key(self) -> None:
        config = _search_config(DEV_SEARCH, "dev")
        self.assertEqual((config.index, config.embedding_deployment), ("u15-demo-documents", "text-embedding-3-small"))
        with self.assertRaisesRegex(SettingsError, "APP_ENV=dev"):
            _search_config(DEV_SEARCH, "local")
        with self.assertRaisesRegex(SettingsError, "AZURE_SEARCH_INDEX"):
            _search_config({k: v for k, v in DEV_SEARCH.items() if k != "AZURE_SEARCH_INDEX"}, "dev")
        with self.assertRaisesRegex(SettingsError, "key"):
            _search_config({**DEV_SEARCH, "AZURE_SEARCH_API_KEY": "x"}, "dev")
        with self.assertRaisesRegex(SettingsError, "search.windows.net"):
            _search_config({**DEV_SEARCH, "AZURE_SEARCH_ENDPOINT": "https://evil.example.com"}, "dev")
        with self.assertRaisesRegex(SettingsError, "SEARCH_PROVIDER"):
            _search_config({"SEARCH_PROVIDER": "elastic"}, "dev")

    def test_settings_object_refuses_search_outside_dev(self) -> None:
        with self.assertRaisesRegex(SettingsError, "SEARCH_PROVIDER=azure"):
            Settings("local", "postgresql://x", {}, None, None, _search_config(DEV_SEARCH, "dev"))


if __name__ == "__main__":
    unittest.main()
