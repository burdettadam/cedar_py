import pytest
from cedar_py import Policy, Engine
from cedar_py.models import Principal, Action, Resource, Context

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
    policy_str = '''
    @id("test_simple")
    permit(
      principal == User::"alice",
      action == Action::"read",
      resource == Document::"doc123"
    );
    '''
    return Policy(policy_str)

@pytest.fixture
def engine_with_simple_policy(simple_policy):
    return Engine(simple_policy)

@pytest.fixture
def office_context():
    return Context(data={"location": "office"})

@pytest.fixture
def home_context():
    return Context(data={"location": "home"})
