"""``APP_ENV``, ``DATABASE_URL`` and ``DEV_AUTH_IDENTITIES`` (`DT-065`): only ``local`` starts the API."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

from _api_support import IDENTITIES, TOKENS

from app.api import __main__ as api_main
from app.api.auth import VIEWER
from app.api.settings import Settings, SettingsError, load_settings

GOOD_IDENTITIES = json.dumps({TOKENS[VIEWER]: {"subject_id": "dev-viewer", "roles": ["VIEWER"]}})


def env(**overrides: str) -> dict[str, str]:
    base = {"APP_ENV": "local", "DATABASE_URL": "postgresql://x@127.0.0.1:5432/inventory",
            "DEV_AUTH_IDENTITIES": GOOD_IDENTITIES}
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None}


class LoadSettingsTest(unittest.TestCase):
    def test_local_starts(self) -> None:
        loaded = load_settings(env())
        self.assertEqual(loaded.app_env, "local")
        self.assertEqual(set(loaded.identities), {TOKENS[VIEWER]})

    def test_deployed_environments_refuse_to_start(self) -> None:
        for app_env in ("dev", "staging", "prod"):
            with self.subTest(app_env), self.assertRaises(SettingsError) as caught:
                load_settings(env(APP_ENV=app_env))
            self.assertIn("refuses to start", str(caught.exception))

    def test_missing_or_unknown_app_env(self) -> None:
        for value in (None, "", "production", "LOCAL"):
            with self.subTest(value), self.assertRaises(SettingsError):
                load_settings(env(APP_ENV=value))

    def test_database_url_is_required(self) -> None:
        with self.assertRaises(SettingsError):
            load_settings(env(DATABASE_URL=None))

    def test_invalid_identity_registries(self) -> None:
        bad = {
            "missing": None,
            "not json": "{",
            "not an object": "[]",
            "empty": "{}",
            "extra key": json.dumps({TOKENS[VIEWER]: {"subject_id": "a", "roles": ["VIEWER"], "x": 1}}),
            "bad token": json.dumps({"dev-short": {"subject_id": "a", "roles": ["VIEWER"]}}),
            "bad subject": json.dumps({TOKENS[VIEWER]: {"subject_id": "Upper Case", "roles": ["VIEWER"]}}),
            "unknown role": json.dumps({TOKENS[VIEWER]: {"subject_id": "a", "roles": ["ROOT"]}}),
            "no roles": json.dumps({TOKENS[VIEWER]: {"subject_id": "a", "roles": []}}),
        }
        from app.api.app import create_app

        for name, value in bad.items():
            with self.subTest(name), self.assertRaises((SettingsError, ValueError)):
                create_app(load_settings(env(DEV_AUTH_IDENTITIES=value)))

    def test_errors_never_contain_the_token(self) -> None:
        text = json.dumps({TOKENS[VIEWER]: {"subject_id": "Bad Subject", "roles": ["VIEWER"]}})
        from app.api.app import create_app

        with self.assertRaises(Exception) as caught:
            create_app(load_settings(env(DEV_AUTH_IDENTITIES=text)))
        self.assertNotIn(TOKENS[VIEWER], str(caught.exception))

    def test_settings_object_refuses_non_local(self) -> None:
        with self.assertRaises(SettingsError):
            Settings("prod", "postgresql://x", IDENTITIES)


class MainTest(unittest.TestCase):
    def test_refused_configuration_never_starts_the_server(self) -> None:
        with mock.patch.dict("os.environ", env(APP_ENV="prod"), clear=True), \
                mock.patch.object(api_main.uvicorn, "run") as run, redirect_stderr(io.StringIO()) as err:
            self.assertEqual(api_main.main(), 1)
        run.assert_not_called()
        self.assertIn("REFUSED", err.getvalue())

    def test_local_serves_on_127_0_0_1_8000(self) -> None:
        with mock.patch.dict("os.environ", env(), clear=True), mock.patch.object(api_main.uvicorn, "run") as run:
            self.assertEqual(api_main.main(), 0)
        _, kwargs = run.call_args
        self.assertEqual((kwargs["host"], kwargs["port"]), ("127.0.0.1", 8000))


class EnvExampleTest(unittest.TestCase):
    """The repository's ``.env.example`` is valid configuration with evidently fictitious values."""

    PATH = Path(__file__).resolve().parents[3] / ".env.example"

    def test_env_example_loads_with_fictitious_identities(self) -> None:
        values = {}
        for line in self.PATH.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.lstrip().startswith("#"):
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip()
        self.assertEqual(set(values), {"APP_ENV", "DATABASE_URL", "DEV_AUTH_IDENTITIES", "LOG_LEVEL"})
        loaded = load_settings(values)
        self.assertEqual(loaded.app_env, "local")
        userinfo = values["DATABASE_URL"].split("//", 1)[1].partition("@")[0]
        self.assertNotIn(":", userinfo)  # no password in the URL
        tokens = json.loads(values["DEV_AUTH_IDENTITIES"])
        self.assertEqual(len(tokens), 4)
        self.assertTrue(all(token.startswith("dev-example-") for token in tokens))


if __name__ == "__main__":
    unittest.main()
