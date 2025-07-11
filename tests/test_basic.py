"""
Basic tests for Cedar-Py
"""



# Import will work once the package is built
# from cedar_py import Policy, PolicySet, Engine
# from cedar_py.models import Principal, Resource, Action, Context



def test_policy_creation():
    """Test that we can create a policy from a string."""
    from cedar_py import Policy
    policy_str = '{"uid": "basic_policy_creation", "effect": "Permit", "principal": {"type": "User", "id": "alice"}, "action": {"type": "Action", "id": "read"}, "resource": {"type": "Document", "id": "doc123"}}'
    policy = Policy(policy_str)
    assert policy is not None



def test_engine_authorization():
    """Test basic authorization decisions."""
    from cedar_py import Policy, Engine
    from cedar_py.models import Principal, Action, Resource
    policy_str = '{"uid": "basic_engine_authorization", "effect": "Permit", "principal": {"type": "User", "id": "alice"}, "action": {"type": "Action", "id": "read"}, "resource": {"type": "Document", "id": "doc123"}}'
    policy = Policy(policy_str)
    engine = Engine(policy)
    # Test direct string usage
    assert engine.is_authorized('User::"alice"', 'Action::"read"', 'Document::"doc123"') is True
    assert engine.is_authorized('User::"bob"', 'Action::"read"', 'Document::"doc123"') is False
    # Test using model objects
    principal = Principal(uid='User::"alice"')
    action = Action(uid='Action::"read"')
    resource = Resource(uid='Document::"doc123"')
    assert engine.is_authorized(principal, action, resource) is True



def test_policy_file(tmp_path):
    """Test loading a policy from a file."""
    from cedar_py import Policy, Engine
    policy_str = '{"uid": "basic_policy_file", "effect": "Permit", "principal": {"type": "User", "id": "alice"}, "action": {"type": "Action", "id": "read"}, "resource": {"type": "Document", "id": "doc123"}}'
    policy_file = tmp_path / "test_policy.cedar"
    policy_file.write_text(policy_str)
    policy = Policy.from_file(str(policy_file))
    engine = Engine(policy)
    assert engine.is_authorized('User::"alice"', 'Action::"read"', 'Document::"doc123"') is True
