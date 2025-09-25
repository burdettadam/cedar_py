"""
Essential End-to-End tests for Cedar-Py.

These tests use the real Cedar Rust backend and verify that
our Python wrapper integrates correctly with the underlying
Cedar policy evaluation engine.

These are intentionally minimal - just enough to ensure the
full integration works end-to-end.
"""

import pytest
from cedar_py import Engine, Policy, PolicySet
from cedar_py.models import Principal, Action, Resource, Context


@pytest.mark.e2e
class TestCedarIntegrationE2E:
    """Essential E2E tests that verify full Cedar integration."""
    
    def test_simple_policy_evaluation(self):
        """Test basic policy evaluation with real Cedar backend."""
        # Create a simple policy
        policy_str = '''
        @id("test_policy")
        permit(
            principal == User::"alice",
            action == Action::"read", 
            resource == Document::"doc123"
        );
        '''
        
        policy = Policy(policy_str)
        engine = Engine(policy)
        
        # Test authorization
        result = engine.is_authorized(
            Principal(uid='User::"alice"'),
            Action(uid='Action::"read"'),
            Resource(uid='Document::"doc123"')
        )
        
        assert result is True
        
        # Test denial
        result = engine.is_authorized(
            Principal(uid='User::"bob"'),
            Action(uid='Action::"read"'),
            Resource(uid='Document::"doc123"')
        )
        
        assert result is False
    
    def test_policy_with_context(self):
        """Test policy evaluation with context using real Cedar backend."""
        policy_str = '''
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
        
        policy = Policy(policy_str)
        engine = Engine(policy)
        
        # Test with matching context
        office_context = Context(data={"location": "office"})
        result = engine.is_authorized(
            "User::\"alice\"",
            "Action::\"read\"", 
            "Document::\"sensitive\"",
            context=office_context
        )
        
        assert result is True
        
        # Test with non-matching context
        home_context = Context(data={"location": "home"})
        result = engine.is_authorized(
            "User::\"alice\"",
            "Action::\"read\"",
            "Document::\"sensitive\"",
            context=home_context
        )
        
        assert result is False
    
    def test_multiple_policies(self):
        """Test PolicySet with multiple policies using real Cedar backend."""
        policy1_str = '''
        @id("alice_read_policy")
        permit(
            principal == User::"alice",
            action == Action::"read",
            resource == Document::"doc1"
        );
        '''
        
        policy2_str = '''
        @id("bob_write_policy")
        permit(
            principal == User::"bob",
            action == Action::"write",
            resource == Document::"doc2"
        );
        '''
        
        policy1 = Policy(policy1_str)
        policy2 = Policy(policy2_str)
        
        policy_set = PolicySet()
        policy_set.add(policy1)
        policy_set.add(policy2)
        
        engine = Engine(policy_set)
        
        # Test alice can read doc1
        assert engine.is_authorized("User::\"alice\"", "Action::\"read\"", "Document::\"doc1\"") is True
        
        # Test bob can write doc2
        assert engine.is_authorized("User::\"bob\"", "Action::\"write\"", "Document::\"doc2\"") is True
        
        # Test alice cannot write doc2 (no policy allows it)
        assert engine.is_authorized("User::\"alice\"", "Action::\"write\"", "Document::\"doc2\"") is False


@pytest.mark.e2e
class TestCedarErrorsE2E:
    """E2E tests for error handling with real Cedar backend."""
    
    def test_invalid_policy_syntax(self):
        """Test that invalid policy syntax raises appropriate error."""
        with pytest.raises(ValueError, match="Invalid Cedar policy syntax"):
            Policy("this is not valid cedar syntax")
    
    def test_json_policy_conversion(self):
        """Test JSON to Cedar policy conversion with real backend."""
        json_policy = '''{
            "uid": "json_policy",
            "effect": "Permit",
            "principal": {"type": "User", "id": "alice"},
            "action": {"type": "Action", "id": "read"},
            "resource": {"type": "Document", "id": "doc123"}
        }'''
        
        # Should successfully create and use JSON policy
        policy = Policy(json_policy)
        engine = Engine(policy)
        
        result = engine.is_authorized(
            "User::\"alice\"",
            "Action::\"read\"", 
            "Document::\"doc123\""
        )
        
        assert result is True