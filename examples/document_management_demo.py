#!/usr/bin/env python3
"""
Real-World Demo: Document Management System with Cedar Authorization

This demo showcases a practical application of Cedar-Py in a document management
system with role-based access control, departmental policies, and contextual
authorization (time-based and location-based access).

This demonstrates enterprise-grade authorization patterns that would be common
in production systems.
"""

from datetime import datetime
from typing import Dict, Optional

from cedar_py import Engine, Policy, PolicySet
from cedar_py.models import Action, Context, Principal, Resource

# Sample document management policies
POLICIES = {
    "admin_full_access": """
        permit(
            principal in Role::"admin",
            action,
            resource
        );
    """,
    "manager_dept_access": """
        permit(
            principal in Role::"manager",
            action in [Action::"read", Action::"edit"],
            resource
        )
        when {
            resource.department == principal.department
        };
    """,
    "employee_read_access": """
        permit(
            principal in Role::"employee",
            action == Action::"read",
            resource
        )
        when {
            resource.department == principal.department ||
            resource.visibility == "public"
        };
    """,
    "sensitive_business_hours": """
        permit(
            principal,
            action,
            resource
        )
        when {
            resource.classification != "sensitive" ||
            (context.time_hour >= 9 && context.time_hour <= 17)
        };
    """,
    "confidential_office_only": """
        permit(
            principal,
            action,
            resource
        )
        when {
            resource.classification != "confidential" ||
            context.location == "office"
        };
    """,
}


class DocumentManagementSystem:
    """Demo document management system with Cedar authorization."""

    def __init__(self):
        self.engine = self._setup_authorization_engine()
        self.users = self._setup_sample_users()
        self.documents = self._setup_sample_documents()

    def _setup_authorization_engine(self) -> Engine:
        """Create and configure the Cedar authorization engine."""
        policy_set = PolicySet()

        for policy_name, policy_text in POLICIES.items():
            policy = Policy(policy_text)
            policy_set.add(policy)

        return Engine(policy_set)

    def _setup_sample_users(self) -> Dict[str, Dict]:
        """Create sample users with different roles and departments."""
        return {
            "alice": {
                "id": 'User::"alice"',
                "role": "admin",
                "department": "IT",
                "name": "Alice Administrator",
            },
            "bob": {
                "id": 'User::"bob"',
                "role": "manager",
                "department": "Engineering",
                "name": "Bob Manager",
            },
            "charlie": {
                "id": 'User::"charlie"',
                "role": "employee",
                "department": "Engineering",
                "name": "Charlie Developer",
            },
            "diana": {
                "id": 'User::"diana"',
                "role": "employee",
                "department": "Marketing",
                "name": "Diana Marketer",
            },
        }

    def _setup_sample_documents(self) -> Dict[str, Dict]:
        """Create sample documents with different classifications."""
        return {
            "public_readme": {
                "id": 'Document::"public_readme"',
                "title": "Company README",
                "department": "IT",
                "classification": "public",
                "visibility": "public",
            },
            "eng_roadmap": {
                "id": 'Document::"eng_roadmap"',
                "title": "Engineering Roadmap 2024",
                "department": "Engineering",
                "classification": "internal",
                "visibility": "internal",
            },
            "salary_data": {
                "id": 'Document::"salary_data"',
                "title": "Salary Information",
                "department": "HR",
                "classification": "confidential",
                "visibility": "restricted",
            },
            "security_audit": {
                "id": 'Document::"security_audit"',
                "title": "Security Audit Report",
                "department": "IT",
                "classification": "sensitive",
                "visibility": "restricted",
            },
        }

    def check_access(
        self,
        username: str,
        action: str,
        document_id: str,
        current_time: Optional[datetime] = None,
        location: str = "office",
    ) -> Dict:
        """
        Check if a user can perform an action on a document.

        Returns detailed authorization information.
        """
        if username not in self.users:
            return {"allowed": False, "reason": "User not found"}

        if document_id not in self.documents:
            return {"allowed": False, "reason": "Document not found"}

        user = self.users[username]
        document = self.documents[document_id]

        # Create Cedar entities
        principal = Principal(user["id"])
        resource = Resource(document["id"])
        action_entity = Action(f'Action::"{action}"')

        # Build context with current conditions
        if current_time is None:
            current_time = datetime.now()

        context = Context(
            {
                "time_hour": current_time.hour,
                "location": location,
                "user_department": user["department"],
                "user_role": user["role"],
            }
        )

        # Make authorization decision
        response = self.engine.authorize(principal, action_entity, resource, context)

        return {
            "allowed": response.allowed,
            "user": user["name"],
            "action": action,
            "document": document["title"],
            "context": {"time": current_time.strftime("%H:%M"), "location": location},
            "decision_details": response.decision,
            "errors": response.errors,
        }

    def demonstrate_access_patterns(self):
        """Run through various access scenarios to demonstrate the system."""
        print("🏢 Document Management System Authorization Demo")
        print("=" * 60)

        scenarios = [
            # Admin access
            ("alice", "read", "public_readme", None, "office"),
            ("alice", "delete", "salary_data", None, "office"),
            # Manager access to their department
            ("bob", "read", "eng_roadmap", None, "office"),
            ("bob", "edit", "eng_roadmap", None, "office"),
            ("bob", "read", "salary_data", None, "office"),  # Should fail - wrong dept
            # Employee access
            ("charlie", "read", "eng_roadmap", None, "office"),  # Same dept
            ("charlie", "read", "public_readme", None, "office"),  # Public doc
            (
                "charlie",
                "edit",
                "eng_roadmap",
                None,
                "office",
            ),  # Should fail - no edit rights
            (
                "diana",
                "read",
                "eng_roadmap",
                None,
                "office",
            ),  # Should fail - wrong dept
            # Time-based access (sensitive documents)
            (
                "alice",
                "read",
                "security_audit",
                datetime(2024, 1, 15, 14, 30),
                "office",
            ),  # Business hours
            (
                "alice",
                "read",
                "security_audit",
                datetime(2024, 1, 15, 22, 30),
                "office",
            ),  # After hours
            # Location-based access (confidential documents)
            ("alice", "read", "salary_data", None, "office"),  # At office
            ("alice", "read", "salary_data", None, "home"),  # Remote
        ]

        for i, (user, action, doc, time_override, location) in enumerate(scenarios, 1):
            result = self.check_access(user, action, doc, time_override, location)

            status = "✅ ALLOWED" if result["allowed"] else "❌ DENIED"
            print(f"\n{i:2d}. {status}")
            print(f"    User: {result['user']}")
            print(f"    Action: {result['action']} on '{result['document']}'")
            print(
                f"    Context: {result['context']['time']} at {result['context']['location']}"
            )

            if not result["allowed"] and "reason" in result:
                print(f"    Reason: {result['reason']}")
            elif result.get("decision_details"):
                print(f"    Matched policies: {len(result['decision_details'])}")


def main():
    """Run the document management system demo."""
    dms = DocumentManagementSystem()
    dms.demonstrate_access_patterns()

    print("\n" + "=" * 60)
    print("🎯 Key Features Demonstrated:")
    print("• Role-based access control (admin, manager, employee)")
    print("• Department-based authorization")
    print(
        "• Document classification levels (public, internal, confidential, sensitive)"
    )
    print("• Time-based policies (business hours for sensitive documents)")
    print("• Location-based policies (office-only for confidential documents)")
    print("• Complex policy composition and evaluation")

    print("\n💡 This demonstrates how Cedar-Py can handle:")
    print("• Enterprise authorization patterns")
    print("• Multi-dimensional access policies")
    print("• Context-aware security decisions")
    print("• Scalable policy management")


if __name__ == "__main__":
    main()
