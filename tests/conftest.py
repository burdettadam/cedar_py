"""
Shared test configuration and fixtures.
"""

import pytest
from unittest.mock import MagicMock, patch

from cedar_py import Engine, Policy
from cedar_py.policy import PolicySet
from cedar_py.models import Action, Context, Principal, Resource

# Mock classes for unit testing
class MockCedarAuthorizer:
    """Mock Cedar authorizer that returns predictable results."""
    
    def __init__(self, default_result=True):
        self.default_result = default_result
        self.last_request = None
    
    def is_authorized(self, policy_set=None, principal=None, action=None, resource=None, context_json=None, entities_json=None):
        """Mock authorization that returns default_result with proper signature."""
        self.last_request = {
            'policy_set': policy_set,
            'principal': principal,
            'action': action, 
            'resource': resource,
            'context_json': context_json,
            'entities_json': entities_json
        }
        return self.default_result

class MockCedarPolicy:
    """Mock Cedar policy for testing."""
    
    def __init__(self, policy_str="", policy_id=None):
        self.policy_str = policy_str
        self._id = policy_id or "test_policy_001"
    
    @property
    def id(self):
        return self._id

class MockCedarPolicySet:
    """Mock Cedar policy set for testing."""
    
    def __init__(self):
        self.policies = {}
    
    def add(self, policy):
        """Mock add policy."""
        self.policies[policy.id] = policy
    
    def remove(self, policy_id):
        """Mock remove policy."""
        if policy_id in self.policies:
            del self.policies[policy_id]
    
    def __len__(self):
        return len(self.policies)


@pytest.fixture(autouse=True)
def patch_cedar_rust_imports(request, mocker):
    """
    Automatically patch Cedar Rust imports for unit tests only.
    
    E2E tests (marked with @pytest.mark.e2e) will skip mocking
    and use the real Cedar backend.
    """
    # Skip mocking for E2E tests
    if hasattr(request, 'node') and request.node.get_closest_marker('e2e'):
        return
    
    # Create shared instances that can be configured by fixtures
    shared_authorizer = MockCedarAuthorizer()
    
    # Patch the RustCedarAuthorizer import used by Engine
    mocker.patch('cedar_py.engine.CedarAuthorizer', return_value=shared_authorizer)
    
    # Patch the specific Rust imports used by policy.py
    mocker.patch('cedar_py.policy.RustCedarPolicy', MockCedarPolicy)
    mocker.patch('cedar_py.policy.RustCedarPolicySet', MockCedarPolicySet)
    
    # Patch the main rust importer imports
    mocker.patch('cedar_py._rust_importer.RustCedarAuthorizer', return_value=shared_authorizer)
    mocker.patch('cedar_py._rust_importer.RustCedarPolicy', MockCedarPolicy) 
    mocker.patch('cedar_py._rust_importer.RustCedarPolicySet', MockCedarPolicySet)
    
    # Store the shared authorizer so fixtures can access it
    mocker.shared_cedar_authorizer = shared_authorizer


# Additional fixture definitions needed by unit tests
@pytest.fixture
def mock_cedar_rust():
    """Mock fixture for general Cedar Rust functionality."""
    return True

@pytest.fixture 
def mock_successful_authorization(mocker):
    """Mock fixture that sets up successful authorization."""
    # This modifies the shared authorizer to return True
    if hasattr(mocker, 'shared_cedar_authorizer'):
        mocker.shared_cedar_authorizer.default_result = True
        # Add a get_call_log method for test compatibility
        def get_call_log():
            if mocker.shared_cedar_authorizer.last_request:
                return [mocker.shared_cedar_authorizer.last_request]
            return []
        mocker.get_call_log = get_call_log
    return mocker

@pytest.fixture
def mock_denied_authorization(mocker):
    """Mock fixture that sets up denied authorization."""
    # This modifies the shared authorizer to return False
    if hasattr(mocker, 'shared_cedar_authorizer'):
        mocker.shared_cedar_authorizer.default_result = False
        # Add a get_call_log method for test compatibility
        def get_call_log():
            if mocker.shared_cedar_authorizer.last_request:
                return [mocker.shared_cedar_authorizer.last_request]
            return []
        mocker.get_call_log = get_call_log
    return mocker

@pytest.fixture
def sample_policy_text():
    """Sample Cedar policy text for testing."""
    return '''
    @id("test_policy")
    permit(
        principal == User::"alice",
        action == Action::"read", 
        resource == Document::"doc123"
    );
    '''

@pytest.fixture
def context_policy_text():
    """Cedar policy with context conditions for testing."""
    return '''
    @id("context_policy")
    permit(
        principal == User::"alice",
        action == Action::"read",
        resource == Document::"sensitive"
    )
    when {
        context.location == "office"
    };
    '''

@pytest.fixture 
def multiple_policies_text():
    """Multiple Cedar policies for testing policy sets."""
    return [
        '''
        @id("alice_read_policy")
        permit(
            principal == User::"alice",
            action == Action::"read",
            resource == Document::"doc1"
        );
        ''',
        '''
        @id("bob_write_policy") 
        permit(
            principal == User::"bob",
            action == Action::"write",
            resource == Document::"doc2"
        );
        '''
    ]

@pytest.fixture
def sample_entities():
    """Sample entity data for testing."""
    return {
        "entities": [
            {"uid": "User::\"alice\"", "attrs": {"name": "Alice"}},
            {"uid": "Document::\"doc123\"", "attrs": {"title": "Test Document"}}
        ]
    }

@pytest.fixture
def authorization_scenarios():
    """Common authorization test scenarios."""
    return [
        {
            "name": "alice_read_doc123",
            "principal": "User::\"alice\"", 
            "action": "Action::\"read\"",
            "resource": "Document::\"doc123\"",
            "expected": True
        },
        {
            "name": "bob_read_doc123", 
            "principal": "User::\"bob\"",
            "action": "Action::\"read\"", 
            "resource": "Document::\"doc123\"",
            "expected": False
        },
        {
            "name": "alice_write_doc123",
            "principal": "User::\"alice\"",
            "action": "Action::\"write\"",
            "resource": "Document::\"doc123\"", 
            "expected": False
        }
    ]

@pytest.fixture
def common_entities():
    """Commonly used entity fixtures bundled together.""" 
    return {
        "alice": Principal(uid='User::"alice"'),
        "bob": Principal(uid='User::"bob"'), 
        "read_action": Action(uid='Action::"read"'),
        "write_action": Action(uid='Action::"write"'),
        "doc123": Resource(uid='Document::"doc123"'),
        "doc456": Resource(uid='Document::"doc456"')
    }


def pytest_configure(config):
    """Configure custom pytest markers.""" 
    config.addinivalue_line("markers", "unit: Unit tests with mocked dependencies")
    config.addinivalue_line("markers", "e2e: End-to-end integration tests")
    config.addinivalue_line("markers", "slow: Slow tests that may take a while to run")


@pytest.fixture
def alice():
    return Principal(uid='User::"alice"')


@pytest.fixture
def bob():
    return Principal(uid='User::"bob"')


@pytest.fixture
def read_action():
    return Action(uid='Action::"read"')


@pytest.fixture
def write_action():
    return Action(uid='Action::"write"')


@pytest.fixture
def doc123():
    return Resource(uid='Document::"doc123"')


@pytest.fixture
def doc456():
    return Resource(uid='Document::"doc456"')


@pytest.fixture
def simple_policy():
    policy_str = """
    @id("test_simple")
    permit(
      principal == User::"alice",
      action == Action::"read",
      resource == Document::"doc123"
    );
    """
    return Policy(policy_str)


@pytest.fixture
def engine_with_simple_policy(simple_policy):
    return Engine(simple_policy)

@pytest.fixture
def engine_with_context_policy(context_policy_text):
    """Engine configured with a context-based policy."""
    policy = Policy(context_policy_text)
    return Engine(policy)

@pytest.fixture 
def engine_with_multiple_policies(multiple_policies_text):
    """Engine configured with multiple policies."""
    policies = [Policy(policy_text) for policy_text in multiple_policies_text]
    policy_set = PolicySet()
    for policy in policies:
        policy_set.add(policy)
    return Engine(policy_set)

@pytest.fixture
def empty_engine():
    """Empty engine for testing policy addition."""
    return Engine()

@pytest.fixture(params=[
    ("alice_read_doc123", "User::\"alice\"", "Action::\"read\"", "Document::\"doc123\"", True),
    ("bob_read_doc123", "User::\"bob\"", "Action::\"read\"", "Document::\"doc123\"", False),
    ("alice_write_doc123", "User::\"alice\"", "Action::\"write\"", "Document::\"doc123\"", False)
])
def authorization_scenario(request):
    """Parameterized authorization scenarios for testing."""
    name, principal, action, resource, expected = request.param
    return {
        "name": name,
        "principal": principal,
        "action": action, 
        "resource": resource,
        "expected": expected
    }


@pytest.fixture
def office_context():
    return Context(data={"location": "office"})


@pytest.fixture
def home_context():
    return Context(data={"location": "home"})
