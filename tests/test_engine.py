"""
Tests for the Engine and authorization functionality of cedar_py.
"""




class TestEngine:
    """Tests for the Engine class."""

    def test_engine_creation(self):
        """Test creating an Engine."""
        # Import inside test function to avoid import errors when package is not built
        from cedar_py import Engine, Policy
        
        policy_str = """
        @id("test_policy")
        permit(
          principal == User::"alice",
          action == Action::"read",
          resource == Document::"doc123"
        );
        """
        
        policy = Policy(policy_str)
        engine = Engine(policy)
        assert engine is not None
    
    def test_empty_engine(self):
        """Test creating an Engine with no policies."""
        # Import inside test function to avoid import errors when package is not built
        from cedar_py import Engine
        
        engine = Engine()  # No policy_set argument needed now
        assert engine is not None
    
    def test_add_policy(self):
        """Test adding a policy to an Engine."""
        # Import inside test function to avoid import errors when package is not built
        from cedar_py import Engine, Policy
        
        policy_str = """
        @id("test_add_policy")
        permit(
          principal == User::"alice",
          action == Action::"read",
          resource == Document::"doc123"
        );
        """
        
        policy = Policy(policy_str)
        engine = Engine()
        engine.add_policy(policy)
        
        # No assertions needed here, just checking that it doesn't raise exceptions


class TestAuthorization:
    """Tests for authorization decisions."""

    def test_simple_allow(self, engine_with_simple_policy, alice, read_action, doc123):
        """Test a simple authorization decision that should be allowed."""
        assert engine_with_simple_policy.is_authorized(alice, read_action, doc123) is True

    def test_simple_deny(self, engine_with_simple_policy, alice, bob, read_action, write_action, doc123, doc456):
        """Test a simple authorization decision that should be denied."""
        # Wrong principal
        assert engine_with_simple_policy.is_authorized(bob, read_action, doc123) is False
        # Wrong action
        assert engine_with_simple_policy.is_authorized(alice, write_action, doc123) is False
        # Wrong resource
        assert engine_with_simple_policy.is_authorized(alice, read_action, doc456) is False

    def test_with_model_objects(self, alice, bob, read_action, write_action, doc123, doc456):
        """Test authorization with model objects using fixtures."""
        from cedar_py import Engine, Policy
        policy_str = """
        @id("test_with_model_objects")
        permit(
          principal == User::"alice",
          action == Action::"read",
          resource == Document::"doc123"
        );
        """
        policy = Policy(policy_str)
        engine = Engine(policy)
        # Test different combinations
        assert engine.is_authorized(alice, read_action, doc123) is True
        assert engine.is_authorized(bob, read_action, doc123) is False
        assert engine.is_authorized(alice, write_action, doc123) is False
        assert engine.is_authorized(alice, read_action, doc456) is False

    def test_with_context(self, alice, read_action, doc123, office_context, home_context):
        """Test authorization with context using fixtures."""
        from cedar_py import Engine, Policy
        policy_str = """
        @id("test_with_context")
        permit(
          principal == User::"alice",
          action == Action::"read",
          resource == Document::"doc123"
        )
        when { context.location == "office" };
        """
        policy = Policy(policy_str)
        engine = Engine(policy)
        # Test with different contexts
        assert engine.is_authorized(alice, read_action, doc123, office_context) is True
        assert engine.is_authorized(alice, read_action, doc123, home_context) is False


class TestAdvancedAuthorization:
    """Tests for more advanced authorization scenarios."""

    def test_multiple_policies(self, alice, bob, read_action, write_action, doc123, doc456):
        """Test authorization with multiple policies using fixtures."""
        from cedar_py import Engine, Policy, PolicySet
        # Create two separate PolicySets, one for each policy
        policy_set1 = PolicySet()
        policy1 = Policy("""
        @id("policy1")
        permit(
          principal == User::"alice",
          action == Action::"read",
          resource == Document::"doc123"
        );
        """)
        policy_set1.add(policy1)
        policy_set2 = PolicySet()
        policy2 = Policy("""
        @id("policy2")
        permit(
          principal == User::"bob",
          action == Action::"write",
          resource == Document::"doc456"
        );
        """)
        policy_set2.add(policy2)
        # Create engines for each policy set
        engine1 = Engine(policy_set1)
        engine2 = Engine(policy_set2)
        # Test different authorization decisions
        assert engine1.is_authorized(alice, read_action, doc123) is True
        assert engine1.is_authorized(bob, write_action, doc456) is False
        assert engine2.is_authorized(alice, read_action, doc123) is False
        assert engine2.is_authorized(bob, write_action, doc456) is True

    def test_detailed_response(self, alice, bob, read_action, doc123):
        """Test getting detailed authorization responses using fixtures."""
        from cedar_py import Engine, Policy
        policy_str = """
        @id("detailed_response_policy")
        permit(
          principal == User::"alice",
          action == Action::"read",
          resource == Document::"doc123"
        );
        """
        policy = Policy(policy_str)
        engine = Engine(policy)
        # Get detailed response for allowed request
        response = engine.authorize(alice, read_action, doc123)
        assert response.allowed is True
        assert len(response.decision) > 0  # Should have at least one policy ID
        assert len(response.errors) == 0
        # Get detailed response for denied request
        response = engine.authorize(bob, read_action, doc123)
        assert response.allowed is False


class TestMigrationFromVakt:
    """Tests for migration patterns from Vakt to Cedar-Py."""

    def test_basic_migration_pattern(self):
        """Test the basic migration pattern from Vakt to Cedar-Py."""
        from cedar_py import Policy, Engine
        from cedar_py.models import Principal, Resource, Action
        # Cedar policy equivalent to the Vakt example in the migration guide
        policy_str = """
        @id("vakt_migration_policy")
        permit(
          principal == User::"admin",
          action in [Action::"create", Action::"delete", Action::"view"],
          resource is User
        );
        """
        # Create policy and engine
        policy = Policy(policy_str)
        engine = Engine(policy)
        # Create model objects using keyword arguments
        admin = Principal(uid='User::"admin"')
        regular = Principal(uid='User::"regular"')
        view = Action(uid='Action::"view"')
        create = Action(uid='Action::"create"')
        delete = Action(uid='Action::"delete"')
        modify = Action(uid='Action::"modify"')
        user123 = Resource(uid='User::"123"')
        user456 = Resource(uid='User::"456"')
        user789 = Resource(uid='User::"789"')
        # Check authorization using model objects
        assert engine.is_authorized(admin, view, user123) is True
        assert engine.is_authorized(admin, create, user456) is True
        assert engine.is_authorized(admin, delete, user789) is True
        # Check with non-admin user (should be denied)
        assert engine.is_authorized(regular, view, user123) is False
        # Check with non-allowed action (should be denied)
        assert engine.is_authorized(admin, modify, user123) is False
