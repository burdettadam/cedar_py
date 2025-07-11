"""
Tests for migrating from Vakt to Cedar-Py.
"""

import pytest
import os
import json
from pathlib import Path
import unittest

from cedar_py.policy import Policy


class TestVaktMigration:
    """Tests demonstrating migration patterns from Vakt to Cedar-Py."""
    
    def test_vakt_style_policy(self):
        """Test a Vakt-style policy migrated to Cedar."""
        # Import inside test function to avoid import errors when package is not built
        try:
            # First try to import Vakt to see if it's available for comparison
            import vakt
            has_vakt = True
        except ImportError:
            has_vakt = False
    
        # Import Cedar-Py
        from cedar_py import Policy, Engine
        from cedar_py.models import Context
    
        # Create a Cedar policy equivalent to the Vakt example from the migration guide
        policy_str = """
        @id("vakt_style_policy")
        permit(
          principal == User::"admin",
          action in [Action::"create", Action::"delete", Action::"view"],
          resource is User
        );
        """
    
        policy = Policy(policy_str)
        engine = Engine(policy)
    
        # Test authorization using Cedar-Py
        assert engine.is_authorized('User::"admin"', 'Action::"view"', 'User::"123"') is True
        assert engine.is_authorized('User::"regular"', 'Action::"view"', 'User::"123"') is False
        
        if has_vakt:
            # Only run this part if Vakt is installed
            from vakt import Guard, MemoryPolicyStorage, Policy as VaktPolicy, Inquiry
            from vakt.rules import RulesChecker
            
            # Create equivalent Vakt policy
            vakt_policy = VaktPolicy(
                uid='1',
                description='Admin can create, delete, and view users',
                effect=VaktPolicy.ALLOW_ACCESS,
                subjects=['admin'],
                resources=['users/<.*>'],
                actions=['create', 'delete', 'view'],
                context={},
            )
            
            # Create policy storage and guard
            storage = MemoryPolicyStorage()
            storage.add(vakt_policy)
            guard = Guard(storage, RulesChecker())
            
            # Check access using Vakt
            inquiry = Inquiry(
                subject='admin',
                resource='users/123',
                action='view'
            )
            assert guard.is_allowed(inquiry) is True
            
            inquiry = Inquiry(
                subject='regular',
                resource='users/123',
                action='view'
            )
            assert guard.is_allowed(inquiry) is False
    
    def test_context_migration(self):
        """Test migrating context-aware policies from Vakt to Cedar."""
        # Import Cedar-Py
        from cedar_py import Policy, Engine
        from cedar_py.models import Context
        
        # Cedar policy with context condition
        policy_str = """
        @id("context_migration_policy")
        permit(
          principal == User::"admin",
          action == Action::"view",
          resource == Document::"sensitive"
        )
        when { context.ip_address like "192.168.*" };
        """
        
        policy = Policy(policy_str)
        engine = Engine(policy)
        
        # Test with different contexts
        allowed_context = Context({"ip_address": "192.168.1.1"})
        denied_context = Context({"ip_address": "10.0.0.1"})
        
        assert engine.is_authorized(
            'User::"admin"', 
            'Action::"view"', 
            'Document::"sensitive"', 
            allowed_context
        ) is True
        
        assert engine.is_authorized(
            'User::"admin"', 
            'Action::"view"', 
            'Document::"sensitive"', 
            denied_context
        ) is False
    
    def test_regex_pattern_migration(self):
        """Test migrating regex patterns from Vakt to Cedar's 'in' operator for hierarchy."""
        # Import Cedar-Py
        from cedar_py import Policy, Engine
        from cedar_py.models import Principal, Resource, Action

        # In Vakt, you might use regex patterns like 'users/<.*>'
        # In Cedar, you would use the 'in' operator with a wildcard pattern
    
        policy_str = """
        @id("regex_pattern_migration_policy")
        permit(
          principal == User::"admin",
          action == Action::"view",
          resource in Document::"reports"
        );
        """
    
        policy = Policy(policy_str)
        engine = Engine(policy)

        # Define entities
        admin = Principal('User::"admin"')
        view_action = Action('Action::"view"')
        reports_collection = Resource('Document::"reports"')
        report1 = Resource('Document::"report1"', parents=[reports_collection])
        report2 = Resource('Document::"report2"', parents=[reports_collection])
        other_doc = Resource('Document::"other_doc"')

        # Check authorization
        assert engine.is_authorized(admin, view_action, report1) is True
        assert engine.is_authorized(admin, view_action, report2) is True
        assert engine.is_authorized(admin, view_action, other_doc) is False


class TestVaktAPIPatterns:
    """Tests demonstrating how to replicate common Vakt API patterns with Cedar-Py."""
    
    def test_inquiry_pattern(self):
        """Test replicating Vakt's Inquiry pattern with Cedar-Py."""
        # In Vakt, you would use an Inquiry object:
        # inquiry = Inquiry(subject='admin', resource='users/123', action='view')
        # allowed = guard.is_allowed(inquiry)
        
        # In Cedar-Py, you can use a helper function to create a similar pattern:
        from cedar_py import Engine, Policy
        from cedar_py.models import Context
        
        # Create a policy
        policy_str = """
        @id("inquiry_pattern_policy")
        permit(
          principal == User::"admin",
          action == Action::"view",
          resource == Document::"doc123"
        );
        """
        
        policy = Policy(policy_str)
        engine = Engine(policy)
        
        # Create a function to replicate Vakt's Inquiry pattern
        def check_access(subject, resource, action, context=None):
            # Convert to Cedar-Py format if needed
            subject_uid = f'User::"{subject}"'
            action_uid = f'Action::"{action}"'
            resource_uid = f'Document::"{resource}"'
            
            # Check authorization
            return engine.is_authorized(subject_uid, action_uid, resource_uid, context)
        
        # Use the function similar to Vakt's API
        assert check_access("admin", "doc123", "view") is True
        assert check_access("user", "doc123", "view") is False


class TestAdvancedVaktMigration(unittest.TestCase):

    def test_context_based_migration(self):
        """Test migrating context-based policies from Vakt."""
        # Import Cedar-Py
        from cedar_py import Policy, Engine
        from cedar_py.models import Principal, Resource, Action, Context

        # Vakt policy with a condition on the request context (e.g., IP address)
        # In Cedar, this is handled using the 'context' variable in the policy

        policy_str = """
        @id("context_based_migration_policy")
        permit(
          principal == User::"alice",
          action == Action::"view",
          resource == Document::"confidential"
        )
        when {
          context.request.ip_address == "192.168.1.100"
        };
        """

        policy = Policy(policy_str)
        engine = Engine(policy)

        # Define entities and context
        user = Principal('User::"alice"')
        action = Action('Action::"view"')
        resource = Resource('Document::"confidential"')
        valid_context = Context(
            data={'request': {'ip_address': '192.168.1.100'}}
        )
        invalid_context = Context(
            data={'request': {'ip_address': '10.0.0.5'}}
        )

        # Check authorization
        assert engine.is_authorized(user, action, resource, context=valid_context) is True
        assert engine.is_authorized(user, action, resource, context=invalid_context) is False

    def test_attribute_based_migration(self):
        """Test migrating attribute-based policies from Vakt."""
        # Import Cedar-Py
        from cedar_py import Policy, Engine
        from cedar_py.models import Principal, Resource, Action

        # Vakt policy that checks for a specific attribute on a resource
        # In Cedar, you access resource attributes directly
        policy_str = """
        @id("attribute_based_migration_policy")
        permit(
          principal == User::"alice",
          action == Action::"view",
          resource == Document::"doc123"
        )
        when { resource.confidentiality == "public" };
        """

        policy = Policy(policy_str)
        engine = Engine(policy)

        # Define entities with attributes
        user = Principal('User::"alice"')
        action = Action('Action::"view"')
        public_doc = Resource(
            'Document::"doc123"',
            attributes={'confidentiality': 'public'}
        )
        private_doc = Resource(
            'Document::"doc456"',
            attributes={'confidentiality': 'private'}
        )

        # Check authorization
        assert engine.is_authorized(user, action, public_doc) is True
        assert engine.is_authorized(user, action, private_doc) is False
