"""
Unit tests for Cedar-Py models.

These tests focus on testing our Python wrapper logic for entities,
without relying on the actual Cedar backend.
"""

import pytest
from pydantic import ValidationError

from cedar_py.models import Entity, Principal, Action, Resource, Context


class TestEntity:
    """Unit tests for the Entity base class."""
    
    @pytest.mark.unit
    def test_entity_creation_with_uid(self):
        """Test creating an Entity with just a UID."""
        entity = Entity(uid='User::"test"')
        assert entity.uid == 'User::"test"'
        assert entity.attributes == {}
        assert entity.parents == []
    
    @pytest.mark.unit 
    def test_entity_creation_with_attributes(self):
        """Test creating an Entity with attributes."""
        attrs = {"role": "admin", "department": "engineering"}
        entity = Entity(uid='User::"test"', attributes=attrs)
        assert entity.uid == 'User::"test"'
        assert entity.attributes == attrs
    
    @pytest.mark.unit
    def test_entity_invalid_uid_type(self):
        """Test that invalid UID types raise ValidationError."""
        with pytest.raises(ValidationError):
            Entity(uid=123)
    
    @pytest.mark.unit
    def test_entity_to_dict_full_uid(self):
        """Test converting entity with full UID format to dict."""
        entity = Entity(uid='User::"alice"', attributes={"role": "admin"})
        result = entity.to_dict()
        
        expected = {
            "uid": {"type": "User", "id": "alice"},
            "attrs": {"role": "admin"}, 
            "parents": []
        }
        assert result == expected
    
    @pytest.mark.unit
    def test_entity_to_dict_simple_uid(self):
        """Test converting entity with simple UID to dict (backward compatibility)."""
        entity = Entity(uid="read", attributes={"scope": "full"})
        result = entity.to_dict()
        
        expected = {
            "uid": {"type": "Action", "id": "read"}, 
            "attrs": {"scope": "full"},
            "parents": []
        }
        assert result == expected
    
    @pytest.mark.unit
    def test_entity_uid_dict_full_uid(self):
        """Test UID dict conversion with full UID."""
        entity = Entity(uid='Document::"doc123"')
        result = entity.uid_dict()
        
        expected = {"type": "Document", "id": "doc123"}
        assert result == expected
    
    @pytest.mark.unit
    def test_entity_uid_dict_simple_uid(self):
        """Test UID dict conversion with simple UID."""
        entity = Entity(uid="write")
        result = entity.uid_dict()
        
        expected = {"type": "Action", "id": "write"}
        assert result == expected
    
    @pytest.mark.unit
    def test_entity_str_representation(self):
        """Test string representation of entity."""
        entity = Entity(uid='User::"test"')
        assert str(entity) == 'User::"test"'
    
    @pytest.mark.unit
    def test_entity_from_dict(self):
        """Test creating entity from dictionary."""
        data = {
            "uid": {"type": "User", "id": "alice"},
            "attrs": {"role": "admin"},
            "parents": []
        }
        entity = Entity.from_dict(data)
        assert entity.uid == 'User::"alice"'
        assert entity.attributes == {"role": "admin"}


class TestPrincipal:
    """Unit tests for Principal entities."""
    
    @pytest.mark.unit
    def test_principal_creation(self):
        """Test creating a Principal."""
        principal = Principal(uid='User::"alice"', attributes={"role": "admin"})
        assert principal.uid == 'User::"alice"'
        assert principal.attributes == {"role": "admin"}
        assert isinstance(principal, Entity)
    
    @pytest.mark.unit
    def test_principal_to_dict(self):
        """Test Principal to_dict conversion.""" 
        principal = Principal(uid='User::"alice"', attributes={"role": "admin"})
        result = principal.to_dict()
        
        expected = {
            "uid": {"type": "User", "id": "alice"},
            "attrs": {"role": "admin"},
            "parents": []
        }
        assert result == expected
    
    @pytest.mark.unit
    def test_principal_from_dict(self):
        """Test creating Principal from dict."""
        data = {
            "uid": {"type": "User", "id": "bob"},
            "attrs": {"department": "sales"}
        }
        principal = Principal.from_dict(data)
        assert principal.uid == 'User::"bob"'
        assert principal.attributes == {"department": "sales"}


class TestAction:
    """Unit tests for Action entities."""
    
    @pytest.mark.unit
    def test_action_creation(self):
        """Test creating an Action."""
        action = Action(uid='Action::"read"', attributes={"scope": "full"})
        assert action.uid == 'Action::"read"'
        assert action.attributes == {"scope": "full"}
    
    @pytest.mark.unit  
    def test_action_simple_uid(self):
        """Test Action with simple UID for backward compatibility."""
        action = Action(uid="write")
        assert action.uid == "write"
        
        result = action.to_dict()
        expected = {
            "uid": {"type": "Action", "id": "write"},
            "attrs": {},
            "parents": []
        }
        assert result == expected


class TestResource:
    """Unit tests for Resource entities."""
    
    @pytest.mark.unit
    def test_resource_creation(self):
        """Test creating a Resource."""
        resource = Resource(uid='Document::"doc123"', attributes={"owner": "alice"})
        assert resource.uid == 'Document::"doc123"'
        assert resource.attributes == {"owner": "alice"}
    
    @pytest.mark.unit
    def test_resource_to_dict(self):
        """Test Resource to_dict conversion."""
        resource = Resource(uid='Document::"doc123"', attributes={"confidential": True})
        result = resource.to_dict()
        
        expected = {
            "uid": {"type": "Document", "id": "doc123"},
            "attrs": {"confidential": True},
            "parents": []
        }
        assert result == expected


class TestContext:
    """Unit tests for Context."""
    
    @pytest.mark.unit
    def test_context_creation(self):
        """Test creating a Context."""
        data = {"location": "office", "time": "daytime"}
        context = Context(data=data)
        assert context.data == data
    
    @pytest.mark.unit
    def test_context_empty(self):
        """Test creating empty Context."""
        context = Context()
        assert context.data == {}
    
    @pytest.mark.unit
    def test_context_to_dict(self):
        """Test Context to_dict conversion."""
        data = {"ip": "192.168.1.1", "secure": True}
        context = Context(data=data)
        result = context.to_dict()
        assert result == data