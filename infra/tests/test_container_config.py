"""Static checks of the container configuration of U7 (`DT-095`, docs/12 §3.2); standard library only.

They do not build or run anything: the end-to-end verification is ``docker compose ... up`` followed by
``infra/docker/smoke.py`` (docs/12 §3.4). Run from the repository root::

    python -m unittest discover -s infra/tests -t infra/tests
"""

from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKER = ROOT / "infra" / "docker"
COMPOSE = ROOT / "infra" / "docker-compose.yml"
DOCKERFILES = {name: DOCKER / f"{name}.Dockerfile" for name in ("backend", "dataset", "frontend")}
APP_SERVICES = ("dataset", "init", "api", "frontend")
# An exact release (major.minor.patch, or major.minor for PostgreSQL), an optional variant and the digest
# of the multi-platform index (docs/12 §3.2, rule 2; `DT-095`).
PINNED = re.compile(r"^[a-z0-9/._-]+:\d+\.\d+(\.\d+)?(-[a-z0-9.-]+)?@sha256:[0-9a-f]{64}$")


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def instructions(path: Path) -> list[tuple[str, str]]:
    """(INSTRUCTION, arguments) of a Dockerfile, with continuation lines joined and comments dropped."""
    joined = re.sub(r"\\\n", " ", text(path))
    result = []
    for line in joined.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            keyword, _, rest = line.partition(" ")
            result.append((keyword.upper(), rest.strip()))
    return result


def final_stage(path: Path) -> list[tuple[str, str]]:
    items = instructions(path)
    last_from = max(i for i, (keyword, _) in enumerate(items) if keyword == "FROM")
    return items[last_from:]


def compose_services() -> dict[str, str]:
    """Raw text of each service block of the compose file."""
    body = text(COMPOSE).split("\nservices:\n", 1)[1].split("\nvolumes:\n", 1)[0]
    blocks = re.split(r"^  ([a-z][a-z0-9_-]*):\n", body, flags=re.MULTILINE)
    return dict(zip(blocks[1::2], blocks[2::2]))


class BaseImages(unittest.TestCase):
    def test_every_base_image_is_an_exact_release(self) -> None:
        for name, path in DOCKERFILES.items():
            for keyword, args in instructions(path):
                if keyword == "FROM":
                    image = args.split()[0]
                    with self.subTest(dockerfile=name, image=image):
                        self.assertRegex(image, PINNED)
                        self.assertNotIn("latest", image)

    def test_postgres_image_is_an_exact_release(self) -> None:
        image = re.search(r"^\s+image:\s*(\S+)", compose_services()["postgres"], re.MULTILINE).group(1)
        self.assertRegex(image, PINNED)
        self.assertTrue(image.startswith("postgres:16."), image)  # PostgreSQL 16 (`DT-055`)


class Images(unittest.TestCase):
    def test_final_stage_runs_without_root(self) -> None:
        for name, path in DOCKERFILES.items():
            users = [args for keyword, args in final_stage(path) if keyword == "USER"]
            with self.subTest(dockerfile=name):
                self.assertTrue(users, "the final stage must switch to an unprivileged user")
                self.assertNotIn(users[-1].split(":")[0], ("root", "0"))

    def test_healthchecks(self) -> None:
        for name in ("backend", "frontend"):
            checks = [args for keyword, args in final_stage(DOCKERFILES[name]) if keyword == "HEALTHCHECK"]
            with self.subTest(dockerfile=name):
                self.assertEqual(len(checks), 1)
                self.assertIn("CMD", checks[0])
        checks = [args for keyword, args in final_stage(DOCKERFILES["dataset"]) if keyword == "HEALTHCHECK"]
        self.assertEqual(checks, ["NONE"])  # one-shot process

    def test_no_secret_reaches_a_layer(self) -> None:
        for name, path in DOCKERFILES.items():
            for keyword, args in instructions(path):
                with self.subTest(dockerfile=name, instruction=keyword):
                    self.assertNotIn(keyword, ("ADD",))  # COPY only: no remote fetches into layers
                    self.assertNotRegex(args.lower(), r"\.env\b|password|secret|token=|api[_-]?key")

    def test_backend_dependencies_come_pinned_from_pyproject(self) -> None:
        project = tomllib.loads(text(ROOT / "backend" / "pyproject.toml"))["project"]
        groups = project["optional-dependencies"]
        for requirement in project["dependencies"] + groups["db"] + groups["api"] + groups["entra"]:
            with self.subTest(requirement=requirement):
                self.assertRegex(requirement, r"^[A-Za-z0-9_.\[\]-]+==[0-9][A-Za-z0-9.]*$")
        self.assertIn("tomllib.load(open('pyproject.toml', 'rb'))", text(DOCKERFILES["backend"]))
        self.assertIn("o['entra']", text(DOCKERFILES["backend"]))  # U11: APP_ENV=dev validates Entra ID tokens
        self.assertNotIn("'test'", text(DOCKERFILES["backend"]))


class BuildContext(unittest.TestCase):
    def test_dockerignore_is_an_allow_list_that_excludes_env_files(self) -> None:
        rules = [line.strip() for line in text(ROOT / ".dockerignore").splitlines()
                 if line.strip() and not line.startswith("#")]
        self.assertEqual(rules[0], "*")
        self.assertIn("**/.env", rules)
        self.assertIn("**/.env.*", rules)
        self.assertFalse([rule for rule in rules if rule.startswith("!") and ".env" in rule])
        self.assertIn("frontend/node_modules", rules)


class Compose(unittest.TestCase):
    def test_ports_are_published_on_loopback_only(self) -> None:
        published = 0
        for service, block in compose_services().items():
            for ports in re.findall(r"^    ports:\n((?:      - .*\n)+)", block + "\n", re.MULTILINE):
                for mapping in re.findall(r"^      - (.*)$", ports, re.MULTILINE):
                    published += 1
                    with self.subTest(service=service, mapping=mapping):
                        self.assertRegex(mapping, r'^"127\.0\.0\.1:\d+:\d+"$')
        self.assertEqual(published, 3)  # postgres, api, frontend

    def test_no_credentials(self) -> None:
        content = text(COMPOSE).lower()
        for word in ("password", "secret", "api_key", "apikey"):
            self.assertNotIn(word, content)
        self.assertIn("postgres_host_auth_method: trust", content)

    def test_app_services_sit_behind_the_profile(self) -> None:
        services = compose_services()
        self.assertEqual(set(services), {"postgres", *APP_SERVICES})
        self.assertNotIn("profiles:", services["postgres"])  # `up -d` keeps starting PostgreSQL only (U2)
        for service in APP_SERVICES:
            with self.subTest(service=service):
                self.assertIn('profiles: ["app"]', services[service])

    def test_api_runs_local_with_the_example_identities(self) -> None:
        api = compose_services()["api"]
        self.assertIn("APP_ENV: local", api)
        self.assertIn("- ../.env.example", api)
        self.assertIn('"127.0.0.1:8000:8000"', api)

    def test_startup_order(self) -> None:
        services = compose_services()
        self.assertIn("service_completed_successfully", services["init"])
        self.assertIn("service_healthy", services["init"])
        self.assertIn("init:\n        condition: service_completed_successfully", services["api"])
        self.assertIn("api:\n        condition: service_healthy", services["frontend"])
        self.assertIn('RUN_AS_OF: "2025-12-31"', services["init"])  # `DT-058`


class Proxy(unittest.TestCase):
    def test_nginx_serves_unprivileged_and_proxies_api_on_the_same_origin(self) -> None:
        conf = text(DOCKER / "nginx.conf")
        self.assertRegex(conf, r"(?m)^\s*listen 8080;")
        self.assertIn("proxy_pass ${API_UPSTREAM};", conf)  # U12: template; local default below
        self.assertIn("proxy_set_header Host $proxy_host;", conf)
        for directive in ("proxy_ssl_server_name on;", "proxy_ssl_verify on;",  # U12: TLS to the internal api FQDN
                          "proxy_ssl_trusted_certificate /etc/ssl/certs/ca-certificates.crt;"):
            self.assertIn(directive, conf)
        self.assertNotIn("proxy_ssl_verify off", conf)
        self.assertRegex(text(DOCKER / "frontend.Dockerfile"), r"(?m)^FROM nginx:[0-9.]+-alpine@sha256:")  # ships ca-certificates
        dockerfile = text(DOCKER / "frontend.Dockerfile")
        self.assertIn("ENV API_UPSTREAM=http://api:8000", dockerfile)
        self.assertIn("envsubst '${API_UPSTREAM}'", dockerfile)  # only this variable: $host, $uri stay nginx's
        active = "\n".join(line for line in conf.splitlines() if not line.lstrip().startswith("#"))
        self.assertNotRegex(active, r"azurecontainerapps|https?://[a-z]")  # no environment URL in the image
        self.assertIn("location /api/ {", conf)
        self.assertIn("pid /tmp/nginx.pid;", conf)
        self.assertNotRegex(conf, r"(?m)^\s*user\s")
        self.assertIn("try_files $uri /index.html;", conf)

    def test_entry_point_reuses_u5(self) -> None:
        source = text(DOCKER / "serve_api.py")
        self.assertIn("from app.api.app import create_app", source)
        self.assertIn("from app.api.settings import SettingsError, load_settings", source)
        self.assertIn('HOST = "0.0.0.0"', source)


if __name__ == "__main__":
    unittest.main()
