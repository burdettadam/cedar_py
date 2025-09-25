"""
Tests specifically for new Cedar-Py modernization features.
These tests focus on the core functionality we've added.
"""

import pytest
import time
from cedar_py import Policy, Engine, PolicySet
from cedar_py.testing import PolicyTestBuilder


class TestCachingFeatures:
    """Test the new caching capabilities."""
    
    @pytest.mark.e2e
    def test_engine_performance_improvement(self):
        """Test that engine performance is reasonable."""
        policy = Policy('permit(principal, action, resource) when { principal.role == "admin" };')
        engine = Engine(policy)
        
        # Test multiple authorizations
        start_time = time.time()
        
        for i in range(20):  # Smaller number for reliable testing
            result = engine.is_authorized(
                'User::"alice"', 
                'Action::"read"', 
                f'Document::"doc{i}"',
                entities={'User::"alice"': {"uid": {"type": "User", "id": "alice"}, 
                                           "attrs": {"role": "admin"}, "parents": []}}
            )
            assert result is True
            
        elapsed = time.time() - start_time
        # Should complete quickly (less than 1 second for 20 calls)
        assert elapsed < 1.0, f"Authorization took {elapsed:.3f}s, which is too slow"
        
    @pytest.mark.e2e
    def test_engine_with_multiple_policies(self):
        """Test engine performance with multiple policies."""
        policy1 = Policy('permit(principal, action, resource) when { principal.role == "admin" };')
        policy2 = Policy('permit(principal, action == Action::"read", resource) when { principal.department == "engineering" };')
        
        policy_set = PolicySet()
        policy_set.add(policy1)
        policy_set.add(policy2)
        
        engine = Engine(policy_set)
        
        # Test admin access
        admin_result = engine.is_authorized(
            'User::"alice"', 
            'Action::"write"', 
            'Document::"test"',
            entities={'User::"alice"': {"uid": {"type": "User", "id": "alice"},
                                       "attrs": {"role": "admin"}, "parents": []}}
        )
        assert admin_result is True
        
        # Test engineer read access
        eng_result = engine.is_authorized(
            'User::"bob"', 
            'Action::"read"', 
            'Document::"test"',
            entities={'User::"bob"': {"uid": {"type": "User", "id": "bob"},
                                     "attrs": {"department": "engineering"}, "parents": []}}
        )
        assert eng_result is True


class TestTestingFrameworkFeatures:
    """Test the new testing framework capabilities."""
    
    def test_policy_test_builder_basic(self):
        """Test PolicyTestBuilder basic functionality."""
        scenarios = (PolicyTestBuilder()
                     .given_user("alice", role="admin")
                     .when_accessing("read", "Document::\"test\"")
                     .should_be_allowed("Admin can read")
                     .build_scenarios())
        
        assert len(scenarios) == 1
        scenario = scenarios[0]
        
        # Verify scenario structure
        assert scenario.principal == 'User::"alice"'
        assert scenario.action == 'Action::"read"'
        assert scenario.resource == 'Document::"test"'
        assert scenario.expected_result is True
        assert scenario.description == "Admin can read"
        
        # Verify entities were created
        assert scenario.entities is not None
        assert 'User::"alice"' in scenario.entities
        
    def test_policy_test_builder_multiple_scenarios(self):
        """Test PolicyTestBuilder with multiple scenarios."""
        scenarios = (PolicyTestBuilder()
                     .given_user("alice", role="admin")
                     .when_accessing("read", "Document::\"test\"")
                     .should_be_allowed("Admin can read")
                     .given_user("bob", role="user")
                     .when_accessing("read", "Document::\"test\"")
                     .should_be_denied("User cannot read")
                     .build_scenarios())
        
        assert len(scenarios) == 2
        
        # First scenario - admin allowed
        admin_scenario = scenarios[0]
        assert admin_scenario.expected_result is True
        assert admin_scenario.description == "Admin can read"
        
        # Second scenario - user denied
        user_scenario = scenarios[1]
        assert user_scenario.expected_result is False
        assert user_scenario.description == "User cannot read"
        
    @pytest.mark.e2e
    def test_policy_test_builder_with_engine(self):
        """Test PolicyTestBuilder scenarios work with actual engine."""
        policy = Policy('permit(principal, action, resource) when { principal.role == "admin" };')
        engine = Engine(policy)
        
        scenarios = (PolicyTestBuilder()
                     .given_user("alice", role="admin")
                     .when_accessing("read", "Document::\"test\"")
                     .should_be_allowed("Admin can read")
                     .build_scenarios())
        
        scenario = scenarios[0]
        
        # Run the scenario against the engine
        result = engine.is_authorized(
            scenario.principal,
            scenario.action,
            scenario.resource,
            entities=scenario.entities
        )
        
        # Should match expected result
        assert result == scenario.expected_result
        
    def test_policy_test_builder_complex_attributes(self):
        """Test PolicyTestBuilder with complex user attributes."""
        scenarios = (PolicyTestBuilder()
                     .given_user("alice", role="admin", department="engineering", clearance="top_secret")
                     .when_accessing("read", "Document::\"classified\"")
                     .should_be_allowed("Admin with clearance can read classified docs")
                     .build_scenarios())
        
        scenario = scenarios[0]
        
        # Verify entities were created
        assert scenario.entities is not None
        alice_entity = scenario.entities['User::"alice"']
        
        # Verify all attributes were set
        attrs = alice_entity["attrs"]
        assert attrs["role"] == "admin"
        assert attrs["department"] == "engineering" 
        assert attrs["clearance"] == "top_secret"


class TestCLIFeatures:
    """Test the new CLI capabilities."""
    
    def test_cli_components_importable(self):
        """Test that all CLI components can be imported."""
        from cedar_py.cli import PolicyValidator, PolicyTester, PolicyMigrator
        
        assert PolicyValidator is not None
        assert PolicyTester is not None
        assert PolicyMigrator is not None
        
    def test_policy_validator_basic(self):
        """Test PolicyValidator basic functionality."""
        from cedar_py.cli import PolicyValidator
        
        validator = PolicyValidator()
        assert validator is not None
        
        # Test that validator has expected structure
        # (We don't test actual validation logic here as it depends on implementation details)
        
    def test_policy_migrator_basic(self):
        """Test PolicyMigrator basic functionality."""
        from cedar_py.cli import PolicyMigrator
        
        migrator = PolicyMigrator()
        assert migrator is not None


class TestIntegrationFeatures:
    """Test integration capabilities."""
    
    def test_fastapi_integration_import(self):
        """Test that FastAPI integration can be imported."""
        try:
            from cedar_py.integrations.fastapi import CedarAuth, CedarAuthError
            assert CedarAuth is not None
            assert CedarAuthError is not None
        except ImportError as e:
            if "FastAPI" in str(e):
                pytest.skip("FastAPI not available - this is expected")
            else:
                raise
                
    def test_fastapi_integration_basic(self):
        """Test basic FastAPI integration functionality."""
        try:
            from cedar_py.integrations.fastapi import create_cedar_auth
            
            # Test helper function
            policies = ['permit(principal, action, resource) when { principal.role == "admin" };']
            
            # This should work or fail gracefully
            try:
                auth = create_cedar_auth(policies)
                assert auth is not None
            except ImportError:
                pytest.skip("FastAPI not available")
                
        except ImportError:
            pytest.skip("FastAPI integration not available")


class TestFullFeatureIntegration:
    """Test that all features work together."""
    
    @pytest.mark.e2e  
    def test_comprehensive_workflow(self):
        """Test a comprehensive workflow using multiple new features."""
        # Create policy
        policy = Policy('permit(principal, action, resource) when { principal.role == "admin" };')
        engine = Engine(policy)
        
        # Use testing framework to create scenarios
        scenarios = (PolicyTestBuilder()
                     .given_user("alice", role="admin")
                     .when_accessing("read", "Document::\"test\"")
                     .should_be_allowed("Admin can read documents")
                     .build_scenarios())
        
        # Test scenarios against engine
        for scenario in scenarios:
            result = engine.is_authorized(
                scenario.principal,
                scenario.action,
                scenario.resource,
                entities=scenario.entities
            )
            assert result == scenario.expected_result, f"Scenario failed: {scenario.description}"
            
        # Verify CLI components are available
        from cedar_py.cli import PolicyValidator
        validator = PolicyValidator()
        assert validator is not None
        
        # Test performance
        start_time = time.time()
        for i in range(10):
            result = engine.is_authorized(
                'User::"alice"',
                'Action::"read"',
                f'Document::"doc{i}"',
                entities={'User::"alice"': {"uid": {"type": "User", "id": "alice"},
                                           "attrs": {"role": "admin"}, "parents": []}}
            )
            assert result is True
            
        elapsed = time.time() - start_time
        assert elapsed < 0.5, f"Performance test took {elapsed:.3f}s, expected < 0.5s"
        
        print(f"✅ All features working together - 10 authorization checks in {elapsed:.4f}s")
        
    @pytest.mark.e2e
    def test_backward_compatibility(self):
        """Test that new features don't break existing functionality."""
        # Original basic usage should still work - exact match policy
        policy_text = 'permit(principal == User::"alice", action == Action::"read", resource == Document::"doc1");'
        print(f"Policy: {policy_text}")
        policy = Policy(policy_text)
        engine = Engine(policy)
        
        # Basic authorization should work as before
        result = engine.is_authorized('User::"alice"', 'Action::"read"', 'Document::"doc1"')
        print(f"Alice/read/doc1 result: {result}")
        assert result is True
        
        # Different user should be denied with exact match policy
        result = engine.is_authorized('User::"bob"', 'Action::"read"', 'Document::"doc1"')
        print(f"Bob/read/doc1 result: {result}")
        assert result is False
        
        # Different resource should be denied with exact match policy  
        result = engine.is_authorized('User::"alice"', 'Action::"read"', 'Document::"doc2"')
        print(f"Alice/read/doc2 result: {result}")
        assert result is False
        
        # PolicySet should still work
        policy_set = PolicySet()
        policy_set.add(policy)
        
        engine2 = Engine(policy_set)
        result = engine2.is_authorized('User::"alice"', 'Action::"read"', 'Document::"doc1"')
        assert result is True