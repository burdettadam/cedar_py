"""
Tests for the models module of cedar_py.
"""

import pytest


class TestEntity:
    """Tests for the Entity base class."""
    
    def test_entity_creation(self):
        """Test creating an Entity."""
        # Import inside test function to avoid import errors when package is not built
        from cedar_py.models import Entity
        
        entity = Entity("Test::entity", {"attr1": "value1", "attr2": 42})
        assert entity.uid == "Test::entity"
        assert entity.attributes == {"attr1": "value1", "attr2": 42}

    def test_entity_creation_invalid_uid(self):
        """Test creating an Entity with an invalid UID."""
        from cedar_py.models import Entity
        with pytest.raises(ValueError):
            Entity("invalid_uid")

    def test_entity_to_dict(self):
        """Test converting an Entity to a dictionary."""
        # Import inside test function to avoid import errors when package is not built
        from cedar_py.models import Entity
        
        entity = Entity("Test::entity", {"attr1": "value1", "attr2": 42})
        entity_dict = entity.to_dict()
        
        assert entity_dict["uid"] == {"type": "Test", "id": "entity"}
        assert entity_dict["attrs"] == {"attr1": "value1", "attr2": 42}
    
    def test_entity_str(self):
        """Test string representation of an Entity."""
        # Import inside test function to avoid import errors when package is not built
        from cedar_py.models import Entity
        
        entity = Entity("Test::entity")
        assert str(entity) == "Test::entity"


class TestPrincipal:
    """Tests for the Principal class."""
    
    def test_principal_creation(self):
        """Test creating a Principal."""
        # Import inside test function to avoid import errors when package is not built
        from cedar_py.models import Principal
        
        # With namespace
        principal = Principal("User::alice", {"role": "admin"})
        assert principal.uid == "User::alice"
        assert principal.attributes == {"role": "admin"}
        
    def test_principal_to_dict(self):
        """Test converting a Principal to a dictionary."""
        # Import inside test function to avoid import errors when package is not built
        from cedar_py.models import Principal
        
        principal = Principal("User::alice", {"role": "admin"})
        principal_dict = principal.to_dict()
        
        assert principal_dict["uid"] == {"type": "User", "id": "alice"}
        assert principal_dict["attrs"] == {"role": "admin"}


class TestResource:
    """Tests for the Resource class."""
    
    def test_resource_creation(self):
        """Test creating a Resource."""
        # Import inside test function to avoid import errors when package is not built
        from cedar_py.models import Resource
        
        # With namespace
        resource = Resource("Document::doc123", {"owner": "alice", "confidential": True})
        assert resource.uid == "Document::doc123"
        assert resource.attributes == {"owner": "alice", "confidential": True}
        
    def test_resource_to_dict(self):
        """Test converting a Resource to a dictionary."""
        # Import inside test function to avoid import errors when package is not built
        from cedar_py.models import Resource
        
        resource = Resource("Document::doc123", {"owner": "alice", "confidential": True})
        resource_dict = resource.to_dict()
        
        assert resource_dict["uid"] == {"type": "Document", "id": "doc123"}
        assert resource_dict["attrs"] == {"owner": "alice", "confidential": True}


class TestAction:
    """Tests for the Action class."""
    
    def test_action_creation(self):
        """Test creating an Action."""
        # Import inside test function to avoid import errors when package is not built
        from cedar_py.models import Action
        
        # With namespace
        action = Action("Action::read", {"scope": "full"})
        assert action.uid == "Action::read"
        assert action.attributes == {"scope": "full"}
        
    def test_action_to_dict(self):
        """Test converting an Action to a dictionary."""
        # Import inside test function to avoid import errors when package is not built
        from cedar_py.models import Action
        
        action = Action("Action::read", {"scope": "full"})
        action_dict = action.to_dict()
        
        assert action_dict["uid"] == {"type": "Action", "id": "read"}
        assert action_dict["attrs"] == {"scope": "full"}


class TestContext:
    """Tests for the Context class."""

    def test_context_creation(self):
        """Test creating a Context object."""
        from cedar_py.models import Context

        context = Context({"request_ip": "127.0.0.1"})
        assert context.data == {"request_ip": "127.0.0.1"}

    def test_context_to_dict(self):
        """Test converting a Context to a dictionary."""
        from cedar_py.models import Context

        context = Context({"request_ip": "127.0.0.1"})
        context_dict = context.to_dict()

        assert context_dict == {"request_ip": "127.0.0.1"}
