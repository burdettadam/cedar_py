"""
Quick Win #3: Policy Development and Testing Framework
A simple but powerful framework for testing Cedar policies with fluent API.
"""

import os
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .engine import Engine
from .models import Action, Context, Principal, Resource
from .policy import Policy, PolicySet


@dataclass
class TestScenario:
    """A test scenario for policy evaluation."""

    name: str
    principal: str
    action: str
    resource: str
    context: Optional[Dict[str, Any]] = None
    entities: Optional[Dict[str, Any]] = None
    expected_result: bool = True
    description: str = ""


class PolicyTestBuilder:
    """Fluent builder for policy test scenarios."""

    def __init__(self):
        self._scenarios: List[TestScenario] = []
        self._current_principal: Optional[str] = None
        self._current_action: Optional[str] = None
        self._current_resource: Optional[str] = None
        self._current_context: Optional[Dict[str, Any]] = None
        self._current_entities: Optional[Dict[str, Any]] = None

    def given_user(self, user_id: str, **attributes) -> "PolicyTestBuilder":
        """Set the principal (user) for the test."""
        self._current_principal = f'User::"{user_id}"'
        if attributes:
            self._current_entities = self._current_entities or {}
            self._current_entities[self._current_principal] = {
                "uid": {"type": "User", "id": user_id},
                "attrs": attributes,
                "parents": [],
            }
        return self

    def given_principal(self, principal: str) -> "PolicyTestBuilder":
        """Set a custom principal for the test."""
        self._current_principal = principal
        return self

    def when_accessing(self, action: str, resource: str) -> "PolicyTestBuilder":
        """Set the action and resource being accessed."""
        self._current_action = (
            f'Action::"{action}"' if not action.startswith("Action::") else action
        )
        self._current_resource = (
            resource
            if resource.startswith('"') or "::" in resource
            else f'Document::"{resource}"'
        )
        return self

    def with_context(self, **context_data) -> "PolicyTestBuilder":
        """Add context data to the test."""
        self._current_context = context_data
        return self

    def with_entities(self, entities: Dict[str, Any]) -> "PolicyTestBuilder":
        """Add custom entities to the test."""
        self._current_entities = entities
        return self

    def should_be_allowed(self, description: str = "") -> "PolicyTestBuilder":
        """Assert that the access should be allowed."""
        self._add_scenario(True, description)
        return self

    def should_be_denied(self, description: str = "") -> "PolicyTestBuilder":
        """Assert that the access should be denied."""
        self._add_scenario(False, description)
        return self

    def should_allow(
        self, user: str, action: str, resource: str, description: str = ""
    ) -> "PolicyTestBuilder":
        """Fluent method to test that access should be allowed."""
        return (
            self.given_user(user)
            .when_accessing(action, resource)
            .should_be_allowed(description)
        )

    def should_deny(
        self, user: str, action: str, resource: str, description: str = ""
    ) -> "PolicyTestBuilder":
        """Fluent method to test that access should be denied."""
        return (
            self.given_user(user)
            .when_accessing(action, resource)
            .should_be_denied(description)
        )

    def build_scenarios(self) -> List[TestScenario]:
        """Build all test scenarios."""
        return self._scenarios.copy()

    def _add_scenario(self, expected_result: bool, description: str):
        """Add a test scenario."""
        if (
            not self._current_principal
            or not self._current_action
            or not self._current_resource
        ):
            raise ValueError(
                "Must specify principal, action, and resource before defining expected result"
            )

        scenario_name = f"{self._current_principal}_{self._current_action}_{self._current_resource}_{expected_result}"

        scenario = TestScenario(
            name=scenario_name,
            principal=self._current_principal,
            action=self._current_action,
            resource=self._current_resource,
            context=self._current_context.copy() if self._current_context else None,
            entities=self._current_entities.copy() if self._current_entities else None,
            expected_result=expected_result,
            description=description,
        )

        self._scenarios.append(scenario)


class PolicyTestCase(unittest.TestCase):
    """
    Base class for Cedar policy testing with fluent API.

    Usage:
        class MyPolicyTests(PolicyTestCase):
            policies = ["user_policies.cedar", "admin_policies.cedar"]

            def test_user_permissions(self):
                self.given_user("alice", department="engineering")
                    .when_accessing("read", "internal_doc")
                    .should_be_allowed()

                self.given_user("bob", department="marketing")
                    .when_accessing("read", "internal_doc")
                    .should_be_denied()
    """

    # Override these in subclasses
    policies: List[str] = []  # List of policy file paths
    policy_content: List[str] = []  # List of policy strings
    schema_file: Optional[str] = None

    def setUp(self):
        """Set up the test environment."""
        self.engine = self._create_engine()
        self.test_builder = PolicyTestBuilder()

    def _create_engine(self) -> Engine:
        """Create Cedar engine with test policies."""
        policies = []

        # Load from files
        for policy_file in self.policies:
            if os.path.exists(policy_file):
                with open(policy_file, "r") as f:
                    content = f.read()
                    policies.append(Policy(content))
            else:
                self.fail(f"Policy file not found: {policy_file}")

        # Load from content
        for content in self.policy_content:
            policies.append(Policy(content))

        if not policies:
            self.fail(
                "No policies specified. Set 'policies' or 'policy_content' class variables."
            )

        policy_set = PolicySet({policy.id: policy for policy in policies})
        return Engine(policy_set)

    def given_user(self, user_id: str, **attributes) -> PolicyTestBuilder:
        """Start building a test scenario with a user."""
        return PolicyTestBuilder().given_user(user_id, **attributes)

    def given_principal(self, principal: str) -> PolicyTestBuilder:
        """Start building a test scenario with a principal."""
        return PolicyTestBuilder().given_principal(principal)

    def should_allow(
        self,
        user: str,
        action: str,
        resource: str,
        context: Optional[Dict] = None,
        entities: Optional[Dict] = None,
    ):
        """Assert that user should be allowed to perform action on resource."""
        principal = f'User::"{user}"'
        action_entity = f'Action::"{action}"'
        resource_entity = resource if "::" in resource else f'Document::"{resource}"'

        context_obj = Context(context) if context else None

        result = self.engine.is_authorized(
            principal=principal,
            action=action_entity,
            resource=resource_entity,
            context=context_obj,
            entities=entities,
        )

        self.assertTrue(
            result,
            f"Expected {user} to be ALLOWED {action} on {resource}, but was DENIED",
        )

    def should_deny(
        self,
        user: str,
        action: str,
        resource: str,
        context: Optional[Dict] = None,
        entities: Optional[Dict] = None,
    ):
        """Assert that user should be denied to perform action on resource."""
        principal = f'User::"{user}"'
        action_entity = f'Action::"{action}"'
        resource_entity = resource if "::" in resource else f'Document::"{resource}"'

        context_obj = Context(context) if context else None

        result = self.engine.is_authorized(
            principal=principal,
            action=action_entity,
            resource=resource_entity,
            context=context_obj,
            entities=entities,
        )

        self.assertFalse(
            result,
            f"Expected {user} to be DENIED {action} on {resource}, but was ALLOWED",
        )

    def run_scenarios(self, scenarios: List[TestScenario]):
        """Run a list of test scenarios."""
        for scenario in scenarios:
            with self.subTest(scenario=scenario.name):
                context_obj = Context(scenario.context) if scenario.context else None

                result = self.engine.is_authorized(
                    principal=scenario.principal,
                    action=scenario.action,
                    resource=scenario.resource,
                    context=context_obj,
                    entities=scenario.entities,
                )

                if scenario.expected_result:
                    self.assertTrue(
                        result,
                        f"Scenario '{scenario.name}': Expected ALLOW but got DENY. {scenario.description}",
                    )
                else:
                    self.assertFalse(
                        result,
                        f"Scenario '{scenario.name}': Expected DENY but got ALLOW. {scenario.description}",
                    )


class PolicyCoverageAnalyzer:
    """Analyze policy coverage from test scenarios."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.tested_policies: set = set()
        self.untested_policies: set = set()

    def analyze_coverage(self, scenarios: List[TestScenario]) -> Dict[str, Any]:
        """Analyze policy coverage from test scenarios."""
        # This is a simplified implementation
        # In practice, you'd need to trace which policies are evaluated

        total_policies = len(self.engine._policy_set._policies)

        return {
            "total_policies": total_policies,
            "tested_policies": len(self.tested_policies),
            "untested_policies": len(self.untested_policies),
            "coverage_percentage": len(self.tested_policies)
            / max(total_policies, 1)
            * 100,
            "suggestions": [
                f"Add tests for policy: {policy_id}"
                for policy_id in self.untested_policies
            ],
        }


# Example test case
class ExamplePolicyTests(PolicyTestCase):
    """Example policy tests demonstrating the framework."""

    policy_content = [
        """
        @id("user_read_own_documents")
        permit(
          principal == User::"alice",
          action == Action::"read",
          resource == Document::"alice_doc"
        );
        """,
        """
        @id("admin_full_access")
        permit(
          principal,
          action,
          resource
        ) when {
          principal.role == "admin"
        };
        """,
        """
        @id("department_document_access")
        permit(
          principal,
          action == Action::"read", 
          resource
        ) when {
          principal.department == resource.department
        };
        """,
    ]

    def test_user_can_read_own_documents(self):
        """Test that users can read their own documents."""
        self.should_allow("alice", "read", "alice_doc")
        self.should_deny("bob", "read", "alice_doc")

    def test_admin_has_full_access(self):
        """Test that admins have full access."""
        admin_entities = {
            'User::"admin_user"': {
                "uid": {"type": "User", "id": "admin_user"},
                "attrs": {"role": "admin"},
                "parents": [],
            }
        }

        self.should_allow("admin_user", "read", "any_doc", entities=admin_entities)
        self.should_allow("admin_user", "write", "any_doc", entities=admin_entities)
        self.should_allow("admin_user", "delete", "any_doc", entities=admin_entities)

    def test_department_based_access(self):
        """Test department-based document access."""
        entities = {
            'User::"eng_user"': {
                "uid": {"type": "User", "id": "eng_user"},
                "attrs": {"department": "engineering"},
                "parents": [],
            },
            'Document::"eng_doc"': {
                "uid": {"type": "Document", "id": "eng_doc"},
                "attrs": {"department": "engineering"},
                "parents": [],
            },
            'User::"marketing_user"': {
                "uid": {"type": "User", "id": "marketing_user"},
                "attrs": {"department": "marketing"},
                "parents": [],
            },
        }

        self.should_allow("eng_user", "read", 'Document::"eng_doc"', entities=entities)
        self.should_deny(
            "marketing_user", "read", 'Document::"eng_doc"', entities=entities
        )

    def test_fluent_api_scenarios(self):
        """Test using the fluent API for complex scenarios."""
        scenarios = (
            self.given_user("alice", role="user", department="engineering")
            .when_accessing("read", "internal_doc")
            .should_be_allowed("Engineering users can read internal docs")
            .given_user("bob", role="user", department="marketing")
            .when_accessing("read", "internal_doc")
            .should_be_denied("Marketing users cannot read internal docs")
            .given_user("admin", role="admin")
            .when_accessing("delete", "any_doc")
            .should_be_allowed("Admins can delete any document")
            .build_scenarios()
        )

        self.run_scenarios(scenarios)


def run_policy_tests(test_class: type) -> Dict[str, Any]:
    """Run policy tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(test_class)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "success_rate": (result.testsRun - len(result.failures) - len(result.errors))
        / max(result.testsRun, 1),
        "details": {
            "failures": [str(failure[1]) for failure in result.failures],
            "errors": [str(error[1]) for error in result.errors],
        },
    }


# CLI-like interface for testing
if __name__ == "__main__":
    """
    Example usage:
    python policy_testing.py
    """
    print("🧪 Running Cedar Policy Tests")
    print("=" * 40)

    # Run example tests
    results = run_policy_tests(ExamplePolicyTests)

    print(f"\n📊 Test Results:")
    print(f"Tests Run: {results['tests_run']}")
    print(f"Failures: {results['failures']}")
    print(f"Errors: {results['errors']}")
    print(f"Success Rate: {results['success_rate']:.1%}")

    if results["failures"] or results["errors"]:
        print(f"\n❌ Issues found:")
        for failure in results["details"]["failures"]:
            print(f"  - {failure}")
        for error in results["details"]["errors"]:
            print(f"  - {error}")
    else:
        print(f"\n✅ All tests passed!")


# Usage examples:
"""
# Define test class
class MyAppPolicyTests(PolicyTestCase):
    policies = ["policies/user_access.cedar", "policies/admin_access.cedar"]
    
    def test_user_document_access(self):
        # Traditional assertion style
        self.should_allow("alice", "read", "public_doc")
        self.should_deny("alice", "delete", "public_doc")
        
    def test_manager_permissions(self):
        # Fluent API style
        scenarios = (self.given_user("manager", role="manager", department="sales")
                        .when_accessing("read", "sales_report")
                        .with_context(location="office", time_of_day="business_hours")
                        .should_be_allowed()
                        
                        .given_user("intern", role="intern", department="sales")
                        .when_accessing("read", "sales_report")
                        .should_be_denied("Interns cannot access sensitive reports")
                        
                        .build_scenarios())
        
        self.run_scenarios(scenarios)

# Run tests
if __name__ == "__main__":
    unittest.main()
"""
