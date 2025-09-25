"""
Improved unit tests for Cedar-Py Engine using enhanced fixtures.

These tests demonstrate how to use fixtures more effectively to:
- Reduce code duplication
- Create more maintainable tests
- Use parameterized testing for scenario coverage
- Improve test readability
"""

import json
import pytest
from unittest.mock import patch

from cedar_py import Engine, Policy
from cedar_py.models import Principal, Action, Resource, Context


class TestEngineUnitImproved:
    """Improved unit tests for Engine class using enhanced fixtures."""
    
    @pytest.mark.unit
    def test_engine_creation_with_policy(self, simple_policy):
        """Test Engine creation with a policy using fixture."""
        engine = Engine(simple_policy)
        
        assert engine is not None
        assert engine._policy_set is not None
    
    @pytest.mark.unit
    def test_empty_engine_creation(self, empty_engine):
        """Test creating empty Engine using fixture."""
        assert empty_engine is not None
        assert empty_engine._policy_set is not None
    
    @pytest.mark.unit
    def test_engine_add_policy(self, empty_engine, sample_policy_text):
        """Test adding policy to engine using fixtures."""
        policy = Policy(sample_policy_text)
        empty_engine.add_policy(policy)
        
        # Verify policy was processed (mock would have logged this)
        mock_policy_set = empty_engine._policy_set
        assert mock_policy_set is not None
    
    @pytest.mark.unit
    def test_is_authorized_with_common_entities(self, empty_engine, common_entities, mock_successful_authorization):
        """Test authorization using common entity fixtures."""
        result = empty_engine.is_authorized(
            common_entities["alice"],
            common_entities["read_action"],
            common_entities["doc123"]
        )
        
        assert result is True
        
        # Verify the mock was called with correct parameters
        call_log = mock_successful_authorization.get_call_log()
        assert len(call_log) == 1
        assert call_log[0]['principal'] == 'User::"alice"'
        assert call_log[0]['action'] == 'Action::"read"'
        assert call_log[0]['resource'] == 'Document::"doc123"'
    
    @pytest.mark.unit 
    def test_is_authorized_with_context(self, empty_engine, common_entities, office_context, mock_successful_authorization):
        """Test authorization with context using fixtures."""
        result = empty_engine.is_authorized(
            common_entities["alice"],
            common_entities["read_action"], 
            common_entities["doc123"],
            context=office_context
        )
        
        assert result is True
        
        # Verify context was serialized and passed to backend
        call_log = mock_successful_authorization.get_call_log()
        assert len(call_log) == 1
        assert call_log[0]['context_json'] is not None
        context_data = json.loads(call_log[0]['context_json'])
        assert context_data['location'] == 'office'
    
    @pytest.mark.unit
    def test_authorization_scenarios_parameterized(self, empty_engine, authorization_scenario, mock_successful_authorization, mock_denied_authorization):
        """Test authorization using parameterized scenarios."""
        # Configure mock based on expected result
        if authorization_scenario["expected"]:
            mock = mock_successful_authorization
        else:
            mock = mock_denied_authorization
            
        result = empty_engine.is_authorized(
            authorization_scenario["principal"],
            authorization_scenario["action"],
            authorization_scenario["resource"]
        )
        
        assert result == authorization_scenario["expected"]
        
        # Verify correct mock was used
        call_log = mock.get_call_log()
        assert len(call_log) == 1
        assert call_log[0]['principal'] == authorization_scenario["principal"]
        assert call_log[0]['action'] == authorization_scenario["action"]
        assert call_log[0]['resource'] == authorization_scenario["resource"]


class TestEngineEntityPreparationImproved:
    """Improved tests for entity preparation using fixtures."""
    
    @pytest.mark.unit
    def test_prepare_entities_with_fixtures(self, empty_engine, common_entities):
        """Test entity preparation using common entity fixtures."""
        # Mock the internal method to capture how entities are prepared
        with patch.object(empty_engine, '_prepare_entities') as mock_prepare:
            mock_prepare.return_value = {
                'User::"alice"': common_entities["alice"].to_dict(),
                'Action::"read"': common_entities["read_action"].to_dict(), 
                'Document::"doc123"': common_entities["doc123"].to_dict()
            }
            
            empty_engine.is_authorized(
                common_entities["alice"],
                common_entities["read_action"],
                common_entities["doc123"]
            )
            
            # Verify _prepare_entities was called with correct parameters
            mock_prepare.assert_called_once()
            args = mock_prepare.call_args[0]
            assert args[0] == common_entities["alice"]
            assert args[1] == common_entities["read_action"] 
            assert args[2] == common_entities["doc123"]
    
    @pytest.mark.unit
    def test_entity_serialization_with_fixtures(self, empty_engine, common_entities, sample_entities):
        """Test entity serialization using entity fixtures."""
        entities_dict = empty_engine._prepare_entities(
            common_entities["alice"],
            common_entities["read_action"],
            common_entities["doc123"],
            sample_entities
        )
        
        # Verify all entities are included in the result
        assert 'User::"alice"' in entities_dict
        assert 'Action::"read"' in entities_dict
        assert 'Document::"doc123"' in entities_dict
        
        # Verify additional entities from sample_entities are included
        for entity in sample_entities["entities"]:
            assert entity["uid"] in entities_dict


# Example of how to use fixtures in data-driven tests
@pytest.mark.unit
@pytest.mark.parametrize("principal,action,resource,expected", [
    ("User::\"alice\"", "Action::\"read\"", "Document::\"doc123\"", True),
    ("User::\"bob\"", "Action::\"read\"", "Document::\"doc123\"", False),
    ("User::\"alice\"", "Action::\"write\"", "Document::\"doc123\"", False),
    ("User::\"alice\"", "Action::\"read\"", "Document::\"secret\"", False),
])
def test_authorization_data_driven(empty_engine, principal, action, resource, expected, mock_successful_authorization, mock_denied_authorization):
    """Data-driven authorization tests using fixtures."""
    # Configure mock based on expected result
    if expected:
        mock = mock_successful_authorization
    else:
        mock = mock_denied_authorization
        
    result = empty_engine.is_authorized(principal, action, resource)
    
    assert result == expected
    
    # Verify the correct mock was called
    call_log = mock.get_call_log()
    assert len(call_log) == 1
    assert call_log[0]['principal'] == principal
    assert call_log[0]['action'] == action
    assert call_log[0]['resource'] == resource