"""
Unit tests for Cedar-Py Engine.

These tests mock the Cedar Rust backend to focus on testing
our Python wrapper logic for the authorization engine.
"""

import json
import pytest
from unittest.mock import patch

from cedar_py import Engine, Policy
from cedar_py.models import Principal, Action, Resource, Context


class TestEngineUnit:
    """Unit tests for the Engine class with mocked Cedar backend."""
    
    @pytest.mark.unit
    def test_engine_creation(self, mock_cedar_rust, sample_policy_text):
        """Test Engine creation with mocked backend."""
        policy = Policy(sample_policy_text)
        engine = Engine(policy)
        
        # Verify that the engine was created and the policy was processed
        assert engine is not None
        assert engine._policy_set is not None
    
    @pytest.mark.unit
    def test_engine_empty_creation(self, mock_cedar_rust):
        """Test creating empty Engine."""
        engine = Engine()
        assert engine is not None
        assert engine._policy_set is not None
    
    @pytest.mark.unit
    def test_engine_add_policy(self, mock_cedar_rust, sample_policy_text):
        """Test adding policy to engine."""
        engine = Engine()
        policy = Policy(sample_policy_text)
        
        engine.add_policy(policy)
        
        # Verify policy was processed (mock would have logged this)
        mock_policy_set = engine._policy_set
        assert mock_policy_set is not None
    
    @pytest.mark.unit
    def test_is_authorized_with_strings(self, mock_successful_authorization):
        """Test authorization check with string inputs."""
        engine = Engine()
        
        result = engine.is_authorized(
            'User::"alice"',
            'Action::"read"', 
            'Document::"doc123"'
        )
        
        assert result is True
        
        # Verify the mock was called with correct parameters
        call_log = mock_successful_authorization.get_call_log()
        assert len(call_log) == 1
        assert call_log[0]['principal'] == 'User::"alice"'
        assert call_log[0]['action'] == 'Action::"read"'
        assert call_log[0]['resource'] == 'Document::"doc123"'
    
    @pytest.mark.unit
    def test_is_authorized_with_entities(self, mock_successful_authorization):
        """Test authorization check with entity objects."""
        engine = Engine()
        
        principal = Principal(uid='User::"alice"')
        action = Action(uid='Action::"read"')
        resource = Resource(uid='Document::"doc123"')
        
        result = engine.is_authorized(principal, action, resource)
        
        assert result is True
        
        # Verify the mock received the entity UIDs
        call_log = mock_successful_authorization.get_call_log()
        assert len(call_log) == 1
        assert call_log[0]['principal'] == 'User::"alice"'
        assert call_log[0]['action'] == 'Action::"read"'
        assert call_log[0]['resource'] == 'Document::"doc123"'
    
    @pytest.mark.unit
    def test_is_authorized_with_context(self, mock_successful_authorization):
        """Test authorization check with context."""
        engine = Engine()
        context = Context(data={"location": "office"})
        
        result = engine.is_authorized(
            'User::"alice"',
            'Action::"read"',
            'Document::"doc123"',
            context=context
        )
        
        assert result is True
        
        # Verify context was serialized and passed to backend
        call_log = mock_successful_authorization.get_call_log()
        assert len(call_log) == 1
        context_json = call_log[0]['context_json']
        assert context_json is not None
        parsed_context = json.loads(context_json)
        assert parsed_context == {"location": "office"}
    
    @pytest.mark.unit
    def test_is_authorized_denied(self, mock_denied_authorization):
        """Test authorization check that returns deny."""
        engine = Engine()
        
        result = engine.is_authorized(
            'User::"bob"',
            'Action::"write"',
            'Document::"secret"'
        )
        
        assert result is False
    
    @pytest.mark.unit
    def test_is_authorized_with_entities_dict(self, mock_successful_authorization):
        """Test authorization with additional entities."""
        engine = Engine()
        
        entities = {
            'User::"manager"': {
                "uid": {"type": "User", "id": "manager"},
                "attrs": {"role": "supervisor"}
            }
        }
        
        result = engine.is_authorized(
            'User::"alice"',
            'Action::"read"',
            'Document::"doc123"',
            entities=entities
        )
        
        assert result is True
        
        # Verify entities were serialized and passed
        call_log = mock_successful_authorization.get_call_log()
        assert len(call_log) == 1
        entities_json = call_log[0]['entities_json']
        assert entities_json is not None
    
    @pytest.mark.unit
    def test_string_to_entity_conversion(self, mock_cedar_rust):
        """Test that string inputs are properly converted to entity objects."""
        engine = Engine()
        
        # Mock the internal method to capture how strings are converted
        with patch.object(engine, '_prepare_entities') as mock_prepare:
            mock_prepare.return_value = {}
            
            engine.is_authorized('User::"alice"', 'Action::"read"', 'Document::"doc123"')
            
            # Verify _prepare_entities was called with converted entities
            mock_prepare.assert_called_once()
            args = mock_prepare.call_args[0]
            
            # Check that strings were converted to appropriate entity types
            assert args[0].uid == 'User::"alice"'  # Principal
            assert args[1].uid == 'Action::"read"'  # Action
            assert args[2].uid == 'Document::"doc123"'  # Resource
            assert isinstance(args[0], Principal)
            assert isinstance(args[1], Action)
            assert isinstance(args[2], Resource)


class TestEngineEntityPreparation:
    """Unit tests for entity preparation logic."""
    
    @pytest.mark.unit
    def test_prepare_entities_basic(self, mock_cedar_rust):
        """Test basic entity preparation."""
        engine = Engine()
        
        principal = Principal(uid='User::"alice"')
        action = Action(uid='Action::"read"')
        resource = Resource(uid='Document::"doc123"')
        
        entities_dict = engine._prepare_entities(principal, action, resource, None)
        
        # Should contain all three entities
        assert len(entities_dict) == 3
        assert 'User::"alice"' in entities_dict
        assert 'Action::"read"' in entities_dict  
        assert 'Document::"doc123"' in entities_dict
    
    @pytest.mark.unit
    def test_prepare_entities_with_additional(self, mock_cedar_rust):
        """Test entity preparation with additional entities."""
        engine = Engine()
        
        principal = Principal(uid='User::"alice"')
        action = Action(uid='Action::"read"')
        resource = Resource(uid='Document::"doc123"')
        
        additional = {
            'User::"manager"': {
                "uid": {"type": "User", "id": "manager"},
                "attrs": {"role": "supervisor"}
            }
        }
        
        entities_dict = engine._prepare_entities(principal, action, resource, additional)
        
        # Should contain all entities
        assert len(entities_dict) == 4
        assert 'User::"alice"' in entities_dict
        assert 'User::"manager"' in entities_dict
    
    @pytest.mark.unit
    def test_entity_serialization(self, mock_cedar_rust):
        """Test that entities are properly serialized for JSON."""
        engine = Engine()
        
        principal = Principal(uid='User::"alice"', attributes={"role": "admin"})
        action = Action(uid='Action::"read"')
        resource = Resource(uid='Document::"doc123"')
        
        entities_dict = engine._prepare_entities(principal, action, resource, None)
        
        # Verify entities have proper structure for serialization
        alice_entity = entities_dict['User::"alice"']
        assert alice_entity == {
            "uid": {"type": "User", "id": "alice"},
            "attrs": {"role": "admin"},
            "parents": []
        }