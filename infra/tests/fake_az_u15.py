"""Fake Azure CLI for the tests of infra/azure/deploy-u15.ps1 (U15, `DT-094`). Standard library only.

It answers only the commands the script uses and never reaches Azure. Every call is recorded in the JSON state file
(``FAKE_AZ_STATE``). Switches: ``FAKE_U15_SKU`` (default ``free``), ``FAKE_U15_OWNER_ROLES`` (``all`` or ``none``),
``FAKE_U15_EMBEDDINGS`` (``1``/``0``) and ``FAKE_U15_RUNTIME_READER`` (``1``: the runtime identity already has the
reader role).
"""

from __future__ import annotations

import json
import os
import sys

TENANT = "6ce4b1ba-ae4f-4887-bd6b-acb3c72039ad"
RG = "/subscriptions/s/resourceGroups/rg-motor-predictivo-dev"
SEARCH = f"{RG}/providers/Microsoft.Search/searchServices/motor-predictivo-search-dev"
OPENAI = f"{RG}/providers/Microsoft.CognitiveServices/accounts/oai-mpa-dev-x"
USER = "7c85d883-0000-4000-8000-000000000001"
RUNTIME = "2b5317cf-0000-4000-8000-000000000002"
READER = "1407120a-92aa-4202-b7e9-c0e197c71c8f"


def load() -> dict:
    path = os.environ["FAKE_AZ_STATE"]
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    return {"argv": [], "assignments": []}


def option(args: list[str], name: str) -> str | None:
    return args[args.index(name) + 1] if name in args else None


def roles_of(principal: str, state: dict) -> list[dict]:
    if principal == USER:
        if os.environ.get("FAKE_U15_OWNER_ROLES", "all") == "none":
            return [{"roleDefinitionName": "Owner", "scope": RG}]
        return [{"roleDefinitionName": "Owner", "scope": RG},
                {"roleDefinitionName": "Search Service Contributor", "scope": SEARCH},
                {"roleDefinitionName": "Search Index Data Contributor", "scope": SEARCH},
                {"roleDefinitionName": "Cognitive Services OpenAI User", "scope": OPENAI}]
    roles = [{"roleDefinitionName": "AcrPull", "scope": f"{RG}/providers/Microsoft.ContainerRegistry/registries/acr"},
             {"roleDefinitionName": "Cognitive Services OpenAI User", "scope": OPENAI}]
    if os.environ.get("FAKE_U15_RUNTIME_READER") == "1":
        roles.append({"roleDefinitionName": "Search Index Data Reader", "scope": SEARCH})
    for a in state["assignments"]:
        if a["principal"] == principal:
            roles.append({"roleDefinitionName": "Search Index Data Reader" if a["role"] == READER else a["role"],
                          "scope": a["scope"]})
    return roles


def answer(args: list[str], state: dict):
    command = " ".join(a for a in args if not a.startswith("-"))

    def starts(prefix: str) -> bool:
        return command == prefix or command.startswith(prefix + " ")

    if starts("account show"):
        return {"tenantId": TENANT}
    if starts("group show"):
        return {"id": RG, "location": "centralus"}
    if starts("search service show"):
        return {"id": SEARCH, "name": "motor-predictivo-search-dev", "location": "Central US",
                "sku": {"name": os.environ.get("FAKE_U15_SKU", "free")}, "status": "running",
                "provisioningState": "Succeeded", "publicNetworkAccess": "Enabled", "disableLocalAuth": False,
                "authOptions": {"aadOrApiKey": {"aadAuthFailureMode": "http401WithBearerChallenge"}},
                "endpoint": "https://motor-predictivo-search-dev.search.windows.net"}
    if starts("resource list"):
        return [{"id": OPENAI, "name": "oai-mpa-dev-x"}]
    if starts("cognitiveservices account deployment list"):
        deps = [{"name": "gpt-41-mini", "properties": {"model": {"name": "gpt-4.1-mini"}, "provisioningState": "Succeeded"}}]
        if os.environ.get("FAKE_U15_EMBEDDINGS", "1") == "1":
            deps.append({"name": "text-embedding-3-small",
                         "properties": {"model": {"name": "text-embedding-3-small"}, "provisioningState": "Succeeded"}})
        return deps
    if starts("cognitiveservices account show"):
        return {"id": OPENAI, "name": "oai-mpa-dev-x", "properties": {"endpoint": "https://oai-mpa-dev-x.openai.azure.com/"}}
    if starts("ad signed-in-user show"):
        print(USER)
        return None
    if starts("identity show"):
        return {"principalId": RUNTIME, "clientId": "d920d9fa-0000-4000-8000-000000000003"}
    if starts("role assignment list"):
        return roles_of(option(args, "--assignee"), state)
    if starts("role assignment create"):
        state["assignments"].append({"principal": option(args, "--assignee-object-id"), "role": option(args, "--role"),
                                     "scope": option(args, "--scope"),
                                     "type": option(args, "--assignee-principal-type")})
        return None
    raise ValueError(f"unexpected command: {' '.join(args)}")


def main() -> int:
    args = sys.argv[1:]
    state = load()
    state["argv"].append(args)
    try:
        value = answer(args, state)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        with open(os.environ["FAKE_AZ_STATE"], "w", encoding="utf-8") as handle:
            json.dump(state, handle)
    if value is not None:
        print(json.dumps(value))
    return 0


if __name__ == "__main__":
    sys.exit(main())
