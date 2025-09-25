"""
Improved End-to-End tests for Cedar-Py using enhanced fixtures.

These tests demonstrate how to use fixtures effectively in E2E tests
to reduce duplication while maintaining real Cedar integration testing.
"""

import pytest
from cedar_py import Engine, Policy


@pytest.mark.e2e
class TestCedarIntegrationE2EImproved:
    """Improved E2E tests using enhanced fixtures."""
    
    def test_simple_policy_evaluation_with_fixtures(self, sample_policy_text, common_entities):
        """Test basic policy evaluation using fixtures."""
        policy = Policy(sample_policy_text)
        engine = Engine(policy)
        
        # Test authorization with fixtures
        result = engine.is_authorized(
            common_entities["alice"],
            common_entities["read_action"],
            common_entities["doc123"]
        )
        
        assert result is True
        
        # Test denial with different user
        result = engine.is_authorized(
            common_entities["bob"],
            common_entities["read_action"],
            common_entities["doc123"]
        )
        
        assert result is False
    
    def test_context_policy_with_fixtures(self, engine_with_context_policy, office_context, home_context):
        """Test context-based policy using fixtures."""
        # Test with matching context
        result = engine_with_context_policy.is_authorized(
            "User::\"alice\"",
            "Action::\"read\"", 
            "Document::\"sensitive\"",
            context=office_context
        )
        
        assert result is True
        
        # Test with non-matching context
        result = engine_with_context_policy.is_authorized(
            "User::\"alice\"",
            "Action::\"read\"",
            "Document::\"sensitive\"",
            context=home_context
        )
        
        assert result is False
    
    def test_multiple_policies_with_fixtures(self, engine_with_multiple_policies):
        """Test multiple policies using fixtures."""
        # Test alice can read doc1
        assert engine_with_multiple_policies.is_authorized(
            "User::\"alice\"", 
            "Action::\"read\"", 
            "Document::\"doc1\""
        ) is True
        
        # Test bob can write doc2
        assert engine_with_multiple_policies.is_authorized(
            "User::\"bob\"", 
            "Action::\"write\"", 
            "Document::\"doc2\""
        ) is True
        
        # Test alice cannot write doc2 (no policy allows it)
        assert engine_with_multiple_policies.is_authorized(
            "User::\"alice\"", 
            "Action::\"write\"", 
            "Document::\"doc2\""
        ) is False


@pytest.mark.e2e
class TestCedarErrorsE2EImproved:
    """Improved E2E error handling tests using fixtures."""
    
    def test_invalid_policy_syntax_with_fixtures(self):
        """Test error handling for invalid policy syntax."""
        invalid_policy_str = 'invalid cedar policy syntax here!'
        
        with pytest.raises(ValueError, match="Invalid Cedar policy syntax"):
            Policy(invalid_policy_str)
    
    def test_json_policy_conversion_with_fixtures(self):
        """Test JSON to Cedar policy conversion using fixtures."""
        policy_json = '''{
            "uid": "test_json_policy",
            "effect": "Permit",
            "principal": {"type": "User", "id": "alice"},
            "action": {"type": "Action", "id": "read"}, 
            "resource": {"type": "Document", "id": "doc123"}
        }'''
        
        policy = Policy(policy_json)
        engine = Engine(policy)
        
        # Test that the converted policy works
        result = engine.is_authorized(
            "User::\"alice\"",
            "Action::\"read\"",
            "Document::\"doc123\""
        )
        
        assert result is True


# Example of using authorization_scenario fixture in E2E tests
@pytest.mark.e2e
class TestParameterizedE2E:
    """Demonstrates parameterized E2E testing with fixtures."""
    
    def test_authorization_scenarios_e2e(self, sample_policy_text, authorization_scenario):
        """Test authorization scenarios end-to-end using parameterized fixtures."""
        policy = Policy(sample_policy_text)
        engine = Engine(policy)
        
        result = engine.is_authorized(
            authorization_scenario["principal"],
            authorization_scenario["action"], 
            authorization_scenario["resource"]
        )
        
        # Note: In E2E tests, we test against the real expected behavior
        # which may differ from the mock expectations in unit tests
        if authorization_scenario["name"] == "alice_read_doc123":
            assert result is True
        else:
            # Other scenarios should be False with the sample policy
            assert result is False