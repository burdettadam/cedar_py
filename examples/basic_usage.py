"""
Cedar-Py Developer Guide: Example Usage

This guide demonstrates how to use Cedar-Py for authorization decisions, context-based policies,
and detailed responses. You do not need to look at the test suite for usage patterns.
Make sure the Cedar-Py package is built and installed before running these examples.
"""

from cedar_py import Engine, Policy
from cedar_py.models import Action, Context, Principal, Resource


def basic_example():
    """
    Basic authorization: allow Alice to read doc123, deny Bob.
    Cedar policy (see example_policy.cedar):
    permit(
      principal == User::"alice",
      action == Action::"read",
      resource == Document::"doc123"
    );
    """
    policy_str = """
    permit(
      principal == User::"alice",
      action == Action::"read",
      resource == Document::"doc123"
    );
    """
    policy = Policy(policy_str)
    engine = Engine(policy)

    print("\n=== Basic Authorization ===")
    # Use quoted IDs for Cedar entities
    print(
        "Alice reading doc123:",
        engine.is_authorized('User::"alice"', 'Action::"read"', 'Document::"doc123"'),
    )
    print(
        "Bob reading doc123:",
        engine.is_authorized('User::"bob"', 'Action::"read"', 'Document::"doc123"'),
    )

    # Using model classes (recommended)
    alice = Principal('User::"alice"')
    bob = Principal('User::"bob"')
    read_action = Action('Action::"read"')
    write_action = Action('Action::"write"')
    doc123 = Resource('Document::"doc123"')

    print("\n=== Using Model Classes ===")
    print("Alice reading doc123:", engine.is_authorized(alice, read_action, doc123))
    print("Alice writing doc123:", engine.is_authorized(alice, write_action, doc123))


def context_example():
    """
    Context-based authorization: allow Alice to read doc123 only at the office.
    Cedar policy:
    permit(
      principal == User::"alice",
      action == Action::"read",
      resource == Document::"doc123"
    )
    when { context.location == "office" };
    """
    policy_str = """
    permit(
      principal == User::"alice",
      action == Action::"read",
      resource == Document::"doc123"
    )
    when { context.location == "office" };
    """
    policy = Policy(policy_str)
    engine = Engine(policy)

    office_context = Context({"location": "office"})
    home_context = Context({"location": "home"})

    print("\n=== Context-Based Authorization ===")
    print(
        "Alice at office:",
        engine.is_authorized(
            'User::"alice"', 'Action::"read"', 'Document::"doc123"', office_context
        ),
    )
    print(
        "Alice at home:",
        engine.is_authorized(
            'User::"alice"', 'Action::"read"', 'Document::"doc123"', home_context
        ),
    )


def detailed_response_example():
    """
    Get detailed authorization responses, including decision and errors.
    """
    policy_str = """
    permit(
      principal == User::"alice",
      action == Action::"read",
      resource == Document::"doc123"
    );
    """
    policy = Policy(policy_str)
    engine = Engine(policy)

    print("\n=== Detailed Authorization Response ===")
    alice = Principal('User::"alice"')
    read_action = Action('Action::"read"')
    doc123 = Resource('Document::"doc123"')
    response = engine.authorize(alice, read_action, doc123)
    print(f"Decision: {response.decision}")
    print(f"Allowed: {response.allowed}")
    print(f"Errors: {response.errors}")

    # Test a negative case
    bob = Principal('User::"bob"')
    write_action = Action('Action::"write"')
    response = engine.authorize(bob, write_action, doc123)
    print(f"\nDecision: {response.decision}")
    print(f"Allowed: {response.allowed}")
    print(f"Errors: {response.errors}")


if __name__ == "__main__":
    print("Cedar-Py Developer Guide Examples")
    basic_example()
    context_example()
    detailed_response_example()
