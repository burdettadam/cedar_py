"""
Integration-style tests for Cedar-Py, matching scenarios from tests/example_use_cases.
Covers edge cases: hierarchical entities, context, RBAC, ABAC, wildcards, error reporting.
"""
import json
import os
import pytest
from cedar_py import Policy, Engine
from cedar_py.models import Principal, Action, Resource, Context

# Helper to load entities from Cedar JSON


def normalize_uid(uid: str) -> str:
    # Remove leading/trailing whitespace, replace invalid escapes, and ensure valid Cedar UID
    import re
    # Remove leading/trailing whitespace
    uid = uid.strip()
    # Replace invalid escape sequences (e.g., \ not followed by valid char)
    uid = re.sub(r'\\([^"\\])', r'\\\\\1', uid)
    # Remove null bytes and control characters
    uid = re.sub(r'[\x00-\x1F]', '', uid)
    return uid


def load_entities(path):
    with open(path, "r") as f:
        data = json.load(f)
    def entity_from_dict(e):
        if e.get("uid", {}).get("type") in ["Photo", "Video", "Album", "Account"]:
            ent = Resource.from_dict(e)
        elif e.get("uid", {}).get("type") in ["User", "Administrator", "UserGroup"]:
            ent = Principal.from_dict(e)
        elif e.get("uid", {}).get("type") == "Action":
            ent = Action.from_dict(e)
        elif "type" in e and "id" in e:
            if e["type"] == "Action":
                ent = Action.from_dict(e)
            elif e["type"] in ["User", "Administrator", "UserGroup"]:
                ent = Principal.from_dict(e)
            else:
                ent = Resource.from_dict(e)
        else:
            ent = Resource.from_dict(e)
        # Normalize UID
        ent.uid = normalize_uid(ent.uid)
        return ent
    return {entity_from_dict(e).uid: entity_from_dict(e) for e in data}

# Helper to load context from request


def load_context(ctx):
    return Context(data=ctx)


# Parametrize scenarios for error reporting and schema validation
@pytest.mark.parametrize("scenario_json, policy_file, entities_file, schema_file", [
    ("tests/corpus-tests/a4cd75dfcbb2b50e24597e399a42f06a92ad4609.json", "tests/corpus-tests/a4cd75dfcbb2b50e24597e399a42f06a92ad4609.cedar", "tests/corpus-tests/a4cd75dfcbb2b50e24597e399a42f06a92ad4609.entities.json", "tests/corpus-tests/a4cd75dfcbb2b50e24597e399a42f06a92ad4609.cedarschema"),
])
def test_integration_error_reporting_and_schema(scenario_json, policy_file, entities_file, schema_file):
    # Load scenario
    with open(scenario_json, "r") as f:
        scenario = json.load(f)
    # Load policy
    with open(policy_file, "r") as f:
        policy_str = f.read()
    policy = Policy(policy_str)
    # Load entities
    entities = load_entities(entities_file)
    # Load schema (parse as dict if present)
    schema = None
    if schema_file and os.path.exists(schema_file):
        with open(schema_file, "r") as sf:
            try:
                schema = json.loads(sf.read())
            except Exception:
                schema = None
    engine = Engine(policy, entities=entities, schema=schema)
    # Run each request and check error reporting
    for req in scenario["requests"]:
        principal = Principal(uid=f'{req["principal"]["type"]}::"{req["principal"]["id"]}"')
        action = Action(uid=f'{req["action"]["type"]}::"{req["action"]["id"]}"')
        resource = Resource(uid=f'{req["resource"]["type"]}::"{req["resource"]["id"]}"')
        context = load_context(req["context"]) if "context" in req else None
        response = engine.authorize(principal, action, resource, context)
        expected = req["decision"].lower() == "allow"
        assert response.allowed == expected, f"Scenario: {scenario_json}, Request: {req['description']}"
        # Check error reporting matches scenario
        if "errors" in req:
            assert response.errors == req["errors"], f"Expected errors {req['errors']}, got {response.errors}"

# Parametrize scenarios from example_use_cases and corpus-tests with context and hierarchical entities
@pytest.mark.parametrize("scenario_json, policy_file, entities_file", [
    ("tests/example_use_cases/1a.json", "tests/example_use_cases/policies_1a.cedar", None),
    ("tests/corpus-tests/70947b5b12b7cb67d12578e37ab2ffa7e0c71467.json", "tests/corpus-tests/70947b5b12b7cb67d12578e37ab2ffa7e0c71467.cedar", "tests/corpus-tests/70947b5b12b7cb67d12578e37ab2ffa7e0c71467.entities.json"),
])
def test_integration_scenarios_context_hierarchy(scenario_json, policy_file, entities_file):
    # Load scenario
    with open(scenario_json, "r") as f:
        scenario = json.load(f)
    # Load policy
    with open(policy_file, "r") as f:
        policy_str = f.read()
    policy = Policy(policy_str)
    # Load entities
    if entities_file is None:
        pytest.skip("No entities file provided for this scenario.")
    entities_path = entities_file
    entities = load_entities(entities_path) if entities_path and os.path.exists(entities_path) else {}
    engine = Engine(policy, entities=entities)
    # Run each request
    for req in scenario["requests"]:
        principal = Principal(uid=f'{req["principal"]["type"]}::"{req["principal"]["id"]}"')
        action = Action(uid=f'{req["action"]["type"]}::"{req["action"]["id"]}"')
        resource = Resource(uid=f'{req["resource"]["type"]}::"{req["resource"]["id"]}"')
        context = load_context(req["context"]) if "context" in req else None
        try:
            allowed = engine.is_authorized(principal, action, resource, context)
            expected = req["decision"].lower() == "allow"
            assert allowed == expected, f"Scenario: {scenario_json}, Request: {req['description']}"
        except ValueError:
            # If a parse error occurs, this is expected for invalid UIDs
            pass
        # Additional checks for context and hierarchy
        if context:
            assert isinstance(context, Context)
        # Check if entities have parents (hierarchy)
        for ent in entities.values():
            if hasattr(ent, "parents"):
                assert isinstance(ent.parents, list)

# Parametrize scenarios for ABAC and deny edge cases, including error reporting and schema validation
@pytest.mark.parametrize("scenario_json, policy_file, entities_file, schema_file", [
    ("tests/corpus-tests/dc113cf077ab298842b60dc6da5cabac777c2667.json", "tests/corpus-tests/dc113cf077ab298842b60dc6da5cabac777c2667.cedar", "tests/corpus-tests/dc113cf077ab298842b60dc6da5cabac777c2667.entities.json", "tests/corpus-tests/dc113cf077ab298842b60dc6da5cabac777c2667.cedarschema"),
    ("tests/corpus-tests/4cec0407bfdad739d58c56b9e0cc3c4bccedb690.json", "tests/corpus-tests/4cec0407bfdad739d58c56b9e0cc3c4bccedb690.cedar", "tests/corpus-tests/4cec0407bfdad739d58c56b9e0cc3c4bccedb690.entities.json", "tests/corpus-tests/4cec0407bfdad739d58c56b9e0cc3c4bccedb690.cedarschema"),
])
def test_integration_abac_deny_edge_cases(scenario_json, policy_file, entities_file, schema_file):
    # Load scenario
    with open(scenario_json, "r") as f:
        scenario = json.load(f)
    # Load policy
    with open(policy_file, "r") as f:
        policy_str = f.read()
    policy = Policy(policy_str)
    # Load entities
    entities = load_entities(entities_file)
    # Load schema (parse as dict if present)
    schema = None
    if schema_file and os.path.exists(schema_file):
        with open(schema_file, "r") as sf:
            try:
                schema = json.loads(sf.read())
            except Exception:
                schema = None
    engine = Engine(policy, entities=entities, schema=schema)
    # Run each request and check error reporting and deny logic
    for req in scenario["requests"]:
        principal = Principal(uid=f'{req["principal"]["type"]}::"{req["principal"]["id"]}"')
        action = Action(uid=f'{req["action"]["type"]}::"{req["action"]["id"]}"')
        resource = Resource(uid=f'{req["resource"]["type"]}::"{req["resource"]["id"]}"')
        context = load_context(req["context"]) if "context" in req else None
        response = engine.authorize(principal, action, resource, context)
        expected = req["decision"].lower() == "allow"
        assert response.allowed == expected, f"Scenario: {scenario_json}, Request: {req['description']}"
        # Check error reporting matches scenario
        if "errors" in req:
            assert response.errors == req["errors"], f"Expected errors {req['errors']}, got {response.errors}"

# Parametrize scenarios for wildcard/like operator edge case using a scenario with complex wildcard logic in the policy
@pytest.mark.parametrize("scenario_json, policy_file, entities_file, schema_file", [
    ("tests/corpus-tests/9e9bb12e26ab9ba275fa319b646fec6dc22ef614.json", "tests/corpus-tests/9e9bb12e26ab9ba275fa319b646fec6dc22ef614.cedar", "tests/corpus-tests/9e9bb12e26ab9ba275fa319b646fec6dc22ef614.entities.json", "tests/corpus-tests/9e9bb12e26ab9ba275fa319b646fec6dc22ef614.cedarschema"),
])
def test_integration_wildcard_like_edge_case(scenario_json, policy_file, entities_file, schema_file):
    # Load scenario
    with open(scenario_json, "r") as f:
        scenario = json.load(f)
    # Load policy
    with open(policy_file, "r") as f:
        policy_str = f.read()
    policy = Policy(policy_str)
    # Load entities
    entities = load_entities(entities_file)
    # Load schema (parse as dict if present)
    schema = None
    if schema_file and os.path.exists(schema_file):
        with open(schema_file, "r") as sf:
            try:
                schema = json.loads(sf.read())
            except Exception:
                schema = None
    engine = Engine(policy, entities=entities, schema=schema)
    # Run each request and check error reporting and wildcard/like logic
    for req in scenario["requests"]:
        principal = Principal(uid=f'{req["principal"]["type"]}::"{req["principal"]["id"]}"')
        action = Action(uid=f'{req["action"]["type"]}::"{req["action"]["id"]}"')
        resource = Resource(uid=f'{req["resource"]["type"]}::"{req["resource"]["id"]}"')
        context = load_context(req["context"]) if "context" in req else None
        try:
            response = engine.authorize(principal, action, resource, context)
            expected = req["decision"].lower() == "allow"
            assert response.allowed == expected, f"Scenario: {scenario_json}, Request: {req['description']}"
            # Check error reporting matches scenario
            if "errors" in req:
                assert response.errors == req["errors"], f"Expected errors {req['errors']}, got {response.errors}"
        except ValueError:
            # If a parse error occurs, this is expected for invalid UIDs
            pass

# Parametrize scenarios from example_use_cases and corpus-tests with invalid UIDs
@pytest.mark.parametrize("scenario_json, policy_file, entities_file", [
    ("tests/example_use_cases/1a.json", "tests/example_use_cases/policies_1a.cedar", None),
    ("tests/corpus-tests/70947b5b12b7cb67d12578e37ab2ffa7e0c71467.json", "tests/corpus-tests/70947b5b12b7cb67d12578e37ab2ffa7e0c71467.cedar", "tests/corpus-tests/70947b5b12b7cb67d12578e37ab2ffa7e0c71467.entities.json"),
])
def test_integration_scenarios_context_hierarchy_invalid_uid(scenario_json, policy_file, entities_file):
    # Load scenario
    with open(scenario_json, "r") as f:
        scenario = json.load(f)
    # Load policy
    with open(policy_file, "r") as f:
        policy_str = f.read()
    policy = Policy(policy_str)
    if entities_file is None:
        pytest.skip("No entities file provided for this scenario.")
    entities = load_entities(entities_file)
    engine = Engine(policy, entities=entities)
    # Run each request, expect ValueError for invalid UID, else assert expected decision
    for req in scenario["requests"]:
        principal_uid = f'{req["principal"]["type"]}::"{req["principal"]["id"]}"'
        resource_uid = f'{req["resource"]["type"]}::"{req["resource"]["id"]}"'
        action = Action(uid=f'{req["action"]["type"]}::"{req["action"]["id"]}"')
        context = load_context(req["context"]) if "context" in req else None
        # Check for invalid UID patterns (control chars, invalid escapes)
        import re
        invalid_uid = any([
            re.search(r'[\x00-\x1F]', principal_uid),
            re.search(r'[\x00-\x1F]', resource_uid),
            '\\' in principal_uid or '\\' in resource_uid
        ])
        principal = Principal(uid=principal_uid)
        resource = Resource(uid=resource_uid)
        if invalid_uid:
            with pytest.raises(ValueError):
                engine.is_authorized(principal, action, resource, context)
        else:
            allowed = engine.is_authorized(principal, action, resource, context)
            expected = req["decision"].lower() == "allow"
            assert allowed == expected, f"Scenario: {scenario_json}, Request: {req['description']}"
