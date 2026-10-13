"""The API fails fast with its own 503 when PostgreSQL accepts TCP but never answers (C14, 2026-10-12).

With the server stopped in Azure the request hung until the frontend proxy gave up (nginx 504 after ~60 s)
instead of the API answering ``SERVICE_UNAVAILABLE``. A closed port (``UNREACHABLE_DB``) is refused at once
and never showed it: here a local socket accepts the connection and stays silent, as that server did.
"""

from __future__ import annotations

import socket
import threading
import time
import unittest
from unittest import mock

from _api_support import TestClient, auth, create_app, settings  # noqa: F401 — sets sys.path first

import psycopg

from app.api.auth import VIEWER
from app.db import read
from app.db.read import CONNECT_TIMEOUT_SECONDS, LazyReadOnlyConnection, read_only_connection

#: The request must end well before the ~60 s of nginx's default proxy_read_timeout.
DEADLINE_SECONDS = CONNECT_TIMEOUT_SECONDS + 10


class SilentServer:
    """Listens on 127.0.0.1 and lets the kernel complete the TCP handshake, but never reads nor answers."""

    def __enter__(self) -> str:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(("127.0.0.1", 0))
        self._socket.listen(8)
        return f"postgresql://nobody@127.0.0.1:{self._socket.getsockname()[1]}/none?sslmode=disable"

    def __exit__(self, *exc: object) -> None:
        self._socket.close()


def run_with_deadline(target, deadline: float):  # noqa: ANN001, ANN201
    """Runs ``target`` in a daemon thread: (finished, result or exception, seconds)."""
    outcome: dict[str, object] = {}

    def body() -> None:
        try:
            outcome["value"] = target()
        except BaseException as exc:  # noqa: BLE001 — reported to the test
            outcome["value"] = exc

    started = time.monotonic()
    thread = threading.Thread(target=body, daemon=True)  # a hang must not block the test run
    thread.start()
    thread.join(deadline)
    return not thread.is_alive(), outcome.get("value"), time.monotonic() - started


class ConnectTimeout(unittest.TestCase):
    def test_every_api_connection_sets_the_timeout(self) -> None:
        calls = []

        def fake_connect(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            calls.append(kwargs)
            return mock.MagicMock()

        with mock.patch.object(read.psycopg, "connect", side_effect=fake_connect):
            with read_only_connection("postgresql://x@h/db"):
                pass
            lazy = LazyReadOnlyConnection("postgresql://x@h/db")
            lazy.execute("SELECT 1")
            lazy.close()
        self.assertEqual([c.get("connect_timeout") for c in calls], [CONNECT_TIMEOUT_SECONDS] * 2)
        self.assertTrue(all(c.get("autocommit") is False for c in calls))  # unchanged: READ ONLY transactions
        self.assertGreaterEqual(CONNECT_TIMEOUT_SECONDS, 2)  # libpq's minimum
        self.assertLess(CONNECT_TIMEOUT_SECONDS, 30)  # far below the proxy's ~60 s

    def test_a_silent_server_fails_fast_with_operational_error(self) -> None:
        with SilentServer() as url:
            lazy = LazyReadOnlyConnection(url)
            finished, value, seconds = run_with_deadline(lambda: lazy.execute("SELECT 1"), DEADLINE_SECONDS)
        self.assertTrue(finished, f"the connection still waited after {DEADLINE_SECONDS} s")
        self.assertIsInstance(value, psycopg.OperationalError)
        self.assertGreaterEqual(seconds, CONNECT_TIMEOUT_SECONDS - 1)  # it waited for the timeout, not refused

    def test_the_api_answers_its_own_503_before_the_proxy_gives_up(self) -> None:
        with SilentServer() as url:
            client = TestClient(create_app(settings(url)), raise_server_exceptions=False)
            finished, response, seconds = run_with_deadline(
                lambda: client.get("/api/v1/products", headers=auth(VIEWER)), DEADLINE_SECONDS)
        self.assertTrue(finished, f"the API still waited after {DEADLINE_SECONDS} s")
        self.assertNotIsInstance(response, BaseException, response)
        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body["error"]["code"], "SERVICE_UNAVAILABLE")
        self.assertNotIn("127.0.0.1", response.text)  # no connection detail leaks
        self.assertNotIn("nobody", response.text)
        self.assertLess(seconds, DEADLINE_SECONDS)


if __name__ == "__main__":
    unittest.main()
