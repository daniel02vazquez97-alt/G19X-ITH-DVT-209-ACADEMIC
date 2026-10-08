"""Fake Azure CLI for the tests of infra/azure/deploy-u11.ps1 (U11, `DT-099`). Standard library only.

It answers only the commands the script uses, with Microsoft Graph-like objects kept in a JSON state file
(``FAKE_AZ_STATE``). It never reaches Azure. Switches: ``FAKE_AZ_ALLOW_CREATE`` (``true``/``false``: the
tenant's "Users can register applications"), ``FAKE_AZ_DENY`` (``create``: app creation is denied).
Request bodies are checked like Graph would: no nested lists, no ``{"value", "Count"}`` wrappers, and a
pre-authorized client may only reference scopes that exist.
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid

TENANT = "6ce4b1ba-ae4f-4887-bd6b-acb3c72039ad"
USER = "0f0f0f0f-1111-4222-8333-444444444444"


def load() -> dict:
    path = os.environ["FAKE_AZ_STATE"]
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    return {"applications": {}, "servicePrincipals": {}, "assignments": [], "calls": []}


def save(state: dict) -> None:
    with open(os.environ["FAKE_AZ_STATE"], "w", encoding="utf-8") as handle:
        json.dump(state, handle)


def out(value) -> int:
    if value is not None:
        print(json.dumps(value))
    return 0


def fail(message: str, code: int = 1) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return code


def option(args: list[str], name: str) -> str | None:
    return args[args.index(name) + 1] if name in args else None


def check_body(value, path: str = "") -> None:
    if isinstance(value, dict):
        if set(value) == {"value", "Count"}:
            raise ValueError(f"PowerShell array wrapper at {path}")
        for key, inner in value.items():
            check_body(inner, f"{path}.{key}")
    elif isinstance(value, list):
        for index, inner in enumerate(value):
            if isinstance(inner, list):
                raise ValueError(f"nested list at {path}[{index}]")
            check_body(inner, f"{path}[{index}]")


def new_app(name: str, audience: str) -> dict:
    return {"id": str(uuid.uuid4()), "appId": str(uuid.uuid4()), "displayName": name, "signInAudience": audience,
            "identifierUris": [], "api": {"requestedAccessTokenVersion": None, "oauth2PermissionScopes": [],
                                          "preAuthorizedApplications": [], "knownClientApplications": []},
            "appRoles": [], "web": {"redirectUris": [], "implicitGrantSettings": {"enableIdTokenIssuance": False,
                                                                               "enableAccessTokenIssuance": False}},
            "spa": {"redirectUris": []}, "publicClient": {"redirectUris": []}, "requiredResourceAccess": [],
            "isFallbackPublicClient": None, "passwordCredentials": [], "keyCredentials": [], "owners": [USER],
            "federatedIdentityCredentials": []}


def graph(state: dict, method: str, uri: str, body) -> int:
    path = uri.replace("https://graph.microsoft.com/v1.0", "")
    if path == "/policies/authorizationPolicy":
        allowed = os.environ.get("FAKE_AZ_ALLOW_CREATE", "true") == "true"
        return out({"defaultUserRolePermissions": {"allowedToCreateApps": allowed}})
    if path == "/me/memberOf/microsoft.graph.directoryRole":
        return out({"value": []})
    match = re.fullmatch(r"/(applications|servicePrincipals)/([0-9a-f-]+)(/.*)?", path.split("?")[0])
    if not match:
        return fail(f"unexpected Graph path {path}")
    collection, object_id, rest = match.group(1), match.group(2), match.group(3) or ""
    objects = state[collection]
    if object_id not in objects:
        return fail("Request_ResourceNotFound", 3)
    item = objects[object_id]
    if rest == "" and method == "GET":
        return out({k: v for k, v in item.items() if k not in ("owners", "federatedIdentityCredentials")})
    if rest == "" and method == "PATCH":
        check_body(body)
        merged = {**item, **body}
        if collection == "applications":
            scopes = {s["id"] for s in merged["api"]["oauth2PermissionScopes"]}
            for pre in merged["api"].get("preAuthorizedApplications", []):
                if not set(pre["delegatedPermissionIds"]) <= scopes:
                    return fail("Property preAuthorizedApplications references a scope that does not exist", 1)
        objects[object_id] = merged
        state["calls"].append(f"PATCH {collection}")
        return out(None)
    if rest == "" and method == "DELETE":
        del objects[object_id]
        state["calls"].append(f"DELETE {collection}")
        return out(None)
    if rest.startswith("/owners") and method == "GET":
        return out({"value": [{"id": owner} for owner in item["owners"]]})
    if rest == "/owners/$ref" and method == "POST":
        item["owners"].append(body["@odata.id"].rsplit("/", 1)[1])
        return out(None)
    if rest == "/federatedIdentityCredentials":
        return out({"value": item["federatedIdentityCredentials"]})
    if rest == "/appRoleAssignedTo" and method == "GET":
        return out({"value": [a for a in state["assignments"] if a["resourceId"] == object_id]})
    if rest == "/appRoleAssignedTo" and method == "POST":
        check_body(body)
        assignment = {**body, "id": str(uuid.uuid4()), "principalType": "User"}
        state["assignments"].append(assignment)
        return out(assignment)
    if rest.startswith("/appRoleAssignedTo/") and method == "DELETE":
        state["assignments"] = [a for a in state["assignments"] if a["id"] != rest.rsplit("/", 1)[1]]
        return out(None)
    return fail(f"unexpected Graph call {method} {path}")


def main(args: list[str]) -> int:
    state = load()
    state["calls"].append(" ".join(args[:3]))
    try:
        if args[:2] == ["account", "show"]:
            return out({"tenantId": TENANT, "name": "Azure for Students", "state": "Enabled", "user": {"type": "user"}})
        if args[:3] == ["ad", "signed-in-user", "show"]:
            return out({"id": USER})
        if args[:3] == ["ad", "app", "list"]:
            name = re.fullmatch(r"displayName eq '(.+)'", option(args, "--filter")).group(1)
            return out([{"id": a["id"], "appId": a["appId"], "displayName": a["displayName"]}
                        for a in state["applications"].values() if a["displayName"] == name])
        if args[:3] == ["ad", "app", "create"]:
            if os.environ.get("FAKE_AZ_DENY") == "create":
                return fail("Insufficient privileges to complete the operation. Authorization_RequestDenied")
            app = new_app(option(args, "--display-name"), option(args, "--sign-in-audience"))
            state["applications"][app["id"]] = app
            return out({"id": app["id"], "appId": app["appId"], "displayName": app["displayName"]})
        if args[:3] == ["ad", "sp", "list"]:
            app_id = re.fullmatch(r"appId eq '(.+)'", option(args, "--filter")).group(1)
            return out([{"id": s["id"], "appId": s["appId"]} for s in state["servicePrincipals"].values()
                        if s["appId"] == app_id])
        if args[:3] == ["ad", "sp", "create"]:
            app = next(a for a in state["applications"].values() if a["appId"] == option(args, "--id"))
            sp = {"id": str(uuid.uuid4()), "appId": app["appId"], "displayName": app["displayName"],
                  "appRoleAssignmentRequired": False, "passwordCredentials": [], "keyCredentials": [], "owners": []}
            state["servicePrincipals"][sp["id"]] = sp
            return out({"id": sp["id"], "appId": sp["appId"], "displayName": sp["displayName"]})
        if args[0] == "rest":
            body = option(args, "--body")
            if body is not None:
                with open(body[1:], encoding="ascii") as handle:  # ASCII: the script must not send anything else
                    body = json.load(handle)
            return graph(state, option(args, "--method"), option(args, "--uri"), body)
        return fail(f"unexpected az command: {' '.join(args)}")
    except ValueError as exc:
        return fail(f"Bad request: {exc}")
    finally:
        save(state)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
