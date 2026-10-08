"""Fake Azure CLI for the read-only and secret stages of infra/azure/deploy-u12.ps1 (U12, `DT-100`).

Standard library only; never reaches Azure. State in ``FAKE_AZ_STATE`` (JSON): the Key Vault secrets created through
the ARM control plane, plus the bodies the script sent (to prove the value never reaches stdout or the disk), and the
custom roles and role assignments the `KeyVaultRole` stage creates. ``FAKE_AZ_DEPLOYER_ROLE`` (default ``Owner``) and
``FAKE_AZ_GITHUB_ROLE`` (default ``Reader``) choose the built-in role of the signed-in user and of the GitHub identity.
``FAKE_AZ_EXISTING=1`` makes the U12 resources exist (as Core and Apps leave them); ``FAKE_AZ_KV_PUBLIC=1``,
``FAKE_AZ_ACR_ADMIN=1``, ``FAKE_AZ_API_PUBLIC=1`` and ``FAKE_AZ_OPEN_RULE=1`` break one setting each. Every call is
recorded in full (``argv``) so the tests can prove the preflight only reads.
"""

from __future__ import annotations

import json
import os
import re
import sys

SUB = "0239bbd1-fc72-4dd7-a816-fcbf29f5a631"
RG = f"/subscriptions/{SUB}/resourceGroups/rg-motor-predictivo-dev"
KV_ID = f"{RG}/providers/Microsoft.KeyVault/vaults/kv-mpa-dev-dymtafh7zjbba"
USER_ID = "11111111-1111-4111-8111-111111111111"
RUNTIME_ID = "44444444-4444-4444-8444-444444444444"
GITHUB_ID = "22222222-2222-4222-8222-222222222222"
BUILT_IN = {  # name -> (id, actions)
    "Owner": ("8e3af657-a8ff-443c-a75c-2fe8c4bcb635", ["*"]),
    "Reader": ("acdd72a7-3385-48ef-bd42-f606fba81ae7", ["*/read"]),
    "Key Vault Contributor": ("f25e0fa2-a7c8-4377-a976-54943a77a395", ["Microsoft.KeyVault/*"]),
    "Container Apps Contributor": ("00000000-0000-4000-8000-0000000000ca", ["Microsoft.App/*"]),
    "Managed Identity Operator": ("00000000-0000-4000-8000-0000000000e0", ["Microsoft.ManagedIdentity/userAssignedIdentities/*/assign/action"]),
}


def definition(name: str, role_id: str, actions: list[str], kind: str = "BuiltInRole", scopes=("/",)) -> dict:
    return {"name": role_id, "roleName": name, "roleType": kind, "assignableScopes": list(scopes),
            "permissions": [{"actions": actions, "notActions": [], "dataActions": [], "notDataActions": []}]}


def resources() -> list[dict]:
    """The Key Vault of U10 and, with FAKE_AZ_EXISTING, the U12 resources as Core and Apps leave them."""
    flag = os.environ.get
    found = [{"id": KV_ID, "name": "kv-mpa-dev-dymtafh7zjbba", "type": "Microsoft.KeyVault/vaults", "properties": {
        "publicNetworkAccess": "Enabled" if flag("FAKE_AZ_KV_PUBLIC") else "Disabled", "enableRbacAuthorization": True,
        "enableSoftDelete": True, "enabledForTemplateDeployment": True, "networkAcls": {"bypass": "AzureServices"}}}]
    if not flag("FAKE_AZ_EXISTING"):
        return found
    app = f"{RG}/providers/Microsoft.App"
    registry = [{"server": "acr.azurecr.io", "identity": "id-mpa-dev-runtime"}]
    return found + [
        {"id": f"{RG}/providers/Microsoft.ContainerRegistry/registries/acrmpadevx", "name": "acrmpadevx",
         "type": "Microsoft.ContainerRegistry/registries", "sku": {"name": "Basic"},
         "properties": {"adminUserEnabled": bool(flag("FAKE_AZ_ACR_ADMIN"))}},
        {"id": f"{RG}/providers/Microsoft.DBforPostgreSQL/flexibleServers/psql-mpa-dev-x", "name": "psql-mpa-dev-x",
         "type": "Microsoft.DBforPostgreSQL/flexibleServers", "sku": {"name": "Standard_B1ms"},
         "properties": {"version": "16", "state": "Ready", "highAvailability": {"mode": "Disabled"}}},
        {"id": f"{app}/managedEnvironments/cae-mpa-dev", "name": "cae-mpa-dev", "type": "Microsoft.App/managedEnvironments",
         "properties": {"workloadProfiles": [{"name": "Consumption", "workloadProfileType": "Consumption"}]}},
        {"id": f"{app}/containerApps/ca-mpa-dev-api", "name": "ca-mpa-dev-api", "type": "Microsoft.App/containerApps",
         "properties": {"configuration": {"ingress": {"external": bool(flag("FAKE_AZ_API_PUBLIC"))}, "registries": registry}}},
        {"id": f"{app}/containerApps/ca-mpa-dev-frontend", "name": "ca-mpa-dev-frontend", "type": "Microsoft.App/containerApps",
         "properties": {"configuration": {"ingress": {"external": True, "allowInsecure": False}, "registries": registry}}},
        {"id": f"{app}/jobs/caj-mpa-dev-bootstrap", "name": "caj-mpa-dev-bootstrap", "type": "Microsoft.App/jobs",
         "properties": {"configuration": {"triggerType": "Manual"}}},
        {"id": f"{RG}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-mpa-dev-runtime",
         "name": "id-mpa-dev-runtime", "type": "Microsoft.ManagedIdentity/userAssignedIdentities"},
    ]


def assignments(s: dict, principal: str) -> list[dict]:
    if principal == RUNTIME_ID:
        return [{"scope": f"{RG}/providers/Microsoft.ContainerRegistry/registries/acrmpadevx", "roleDefinitionName": "AcrPull",
                 "roleDefinitionId": "/x/roleDefinitions/7f951dda-4ed3-4680-a7ca-43fe172d538d"}]
    role = os.environ.get("FAKE_AZ_DEPLOYER_ROLE" if principal == USER_ID else "FAKE_AZ_GITHUB_ROLE",
                          "Owner" if principal == USER_ID else "Reader")
    found = [{"scope": f"/subscriptions/{SUB}" if principal == USER_ID else RG, "roleDefinitionName": role,
              "roleDefinitionId": f"/subscriptions/{SUB}/providers/Microsoft.Authorization/roleDefinitions/{BUILT_IN[role][0]}"}]
    return found + [a for a in s.get("assignments", []) if a["principal"] == principal]


def state() -> dict:
    path = os.environ["FAKE_AZ_STATE"]
    return json.load(open(path)) if os.path.exists(path) else {"secrets": {}, "puts": 0, "calls": [], "roles": [],
                                                                "assignments": []}


def out(value) -> int:
    print(json.dumps(value))
    return 0


def option(args, name):
    return args[args.index(name) + 1] if name in args else None


def main(args: list[str]) -> int:
    s = state()
    s["calls"].append(" ".join(args[:4]))
    s.setdefault("argv", []).append(args)
    try:
        if args[:2] == ["account", "show"]:
            return out({"id": SUB, "tenantId": "6ce4b1ba-ae4f-4887-bd6b-acb3c72039ad", "name": "Azure for Students",
                        "state": "Enabled", "user": {"type": "user"}})
        if args[:2] == ["group", "exists"]:
            print("true")
            return 0
        if args[:2] == ["bicep", "build-params"]:
            params = {"parameters": {"keyVaultName": {"value": "kv-mpa-dev-dymtafh7zjbba"}}}
            return out({"parametersJson": json.dumps(params), "templateJson": "{}"})
        if args[:2] == ["group", "show"]:
            return out({"id": RG, "name": "rg-motor-predictivo-dev", "location": "centralus"})
        if args[:2] == ["resource", "list"]:
            wanted = option(args, "--resource-type")
            return out([{"id": r["id"], "name": r["name"], "type": r["type"]} for r in resources()
                        if wanted in (None, r["type"])])
        if args[:2] == ["resource", "show"]:
            rid = option(args, "--ids") or f"{RG}/providers/{option(args, '--resource-type')}/{option(args, '--name')}"
            found = [r for r in resources() if r["id"].lower() == rid.lower()]
            if not found:
                print("ERROR: (ResourceNotFound)", file=sys.stderr)
                return 3
            return out(found[0])
        if args[0] == "rest" and option(args, "--method") == "get" and "/capabilities" in option(args, "--uri"):
            return out({"value": [{"supportedServerEditions": [{"name": "Burstable", "supportedServerSkus": [
                {"name": "Standard_B1ms"}]}], "supportedServerVersions": [{"name": "16"}]}]})
        if args[0] == "rest" and option(args, "--method") == "get" and "require_secure_transport" in option(args, "--uri"):
            return out({"properties": {"value": "on"}})
        if args[0] == "rest" and option(args, "--method") == "get" and "/firewallRules" in option(args, "--uri"):
            ip = "0.0.0.0" if os.environ.get("FAKE_AZ_OPEN_RULE") else "20.1.2.3"
            return out({"value": [{"name": f"aca-out-{ip.replace('.', '-')}",
                                   "properties": {"startIpAddress": ip, "endIpAddress": ip}}]})
        if args[:2] == ["bicep", "build"] or args[:2] == ["bicep", "lint"]:
            return out({}) if args[1] == "build" else 0
        if args[0] == "rest":
            uri = option(args, "--uri")
            match = re.fullmatch(rf"https://management\.azure\.com{re.escape(KV_ID)}/secrets/([a-z-]+)\?api-version=[0-9-]+", uri)
            if not match:
                print(f"ERROR: unexpected uri {uri}", file=sys.stderr)
                return 1
            name, method = match.group(1), option(args, "--method")
            if method == "get":
                if name not in s["secrets"]:
                    print("ERROR: (SecretNotFound)", file=sys.stderr)
                    return 3
                return out({"id": f"{KV_ID}/secrets/{name}", "properties": {}})  # the control plane never returns values
            if method == "put":
                body = json.load(open(option(args, "--body")[1:], encoding="ascii"))
                s["secrets"][name] = body["properties"]["value"]
                s["puts"] += 1
                return 0
        if args[:3] == ["ad", "signed-in-user", "show"]:
            print(USER_ID)
            return 0
        if args[:3] == ["role", "definition", "list"]:
            name = option(args, "--name")
            found = [definition(n, i, a) for n, (i, a) in BUILT_IN.items() if name in (n, i)]
            found += [r for r in s["roles"] if name in (r["roleName"], r["name"])]
            return out(found)
        if args[:3] == ["role", "definition", "create"]:
            body = json.load(open(option(args, "--role-definition")[1:], encoding="ascii"))
            s["roles"].append(definition(body["Name"], "33333333-3333-4333-8333-333333333333", body["Actions"],
                                         "CustomRole", body["AssignableScopes"]))
            return out(s["roles"][-1])
        if args[:3] == ["role", "assignment", "list"]:
            if option(args, "--assignee") is None:  # roles on a resource (the registry)
                return out([{"roleDefinitionName": "AcrPull"}, {"roleDefinitionName": "AcrPush"}])
            return out(assignments(s, option(args, "--assignee")))
        if args[:3] == ["role", "assignment", "create"]:
            role = next(r for r in s["roles"] if r["name"] == option(args, "--role"))
            s["assignments"].append({"principal": option(args, "--assignee-object-id"), "scope": option(args, "--scope"),
                                     "roleDefinitionName": role["roleName"],
                                     "roleDefinitionId": f"{RG}/providers/Microsoft.Authorization/roleDefinitions/{role['name']}"})
            return out(s["assignments"][-1])
        if args[:2] == ["provider", "show"]:
            if "--query" in args and "locations" in option(args, "--query"):
                return out(["Central US", "East US"])
            print("Registered")
            return 0
        if args[:3] == ["postgres", "flexible-server", "list-skus"]:
            return out([{"supportedServerEditions": [{"name": "Burstable", "supportedServerSkus": [{"name": "Standard_B1ms"}]}]}])
        if args[:2] == ["identity", "show"]:
            if option(args, "--name") == "id-mpa-dev-runtime":
                if not os.environ.get("FAKE_AZ_EXISTING"):
                    print("ERROR: (ResourceNotFound)", file=sys.stderr)
                    return 3
                return out({"name": "id-mpa-dev-runtime", "clientId": "r", "principalId": RUNTIME_ID})
            return out({"name": "id-mpa-dev-github", "clientId": "c", "principalId": GITHUB_ID})
        if args[:3] == ["identity", "federated-credential", "list"]:
            return out([{"subject": "repo:o/r:environment:dev"}])
        print(f"ERROR: unexpected az command: {' '.join(args)}", file=sys.stderr)
        return 1
    finally:
        json.dump(s, open(os.environ["FAKE_AZ_STATE"], "w"))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
