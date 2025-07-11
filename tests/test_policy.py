"""
Tests for the Policy and PolicySet classes of cedar_py.
"""




class TestPolicy:
    """Tests for the Policy class."""
    
    def test_policy_from_string(self):
        """Test creating a Policy from a string."""
        from cedar_py import Policy
        policy_str = """
        permit(
          principal == User::"alice",
          action == Action::"read",
          resource == Document::"doc123"
        );
        """
        policy = Policy(policy_str)
        assert policy is not None
        
    def test_policy_from_file(self, tmp_path):
        """Test creating a Policy from a file."""
        from cedar_py import Policy
        policy_str = """
        permit(
          principal == User::"alice",
          action == Action::"read",
          resource == Document::"doc123"
        );
        """
        policy_file = tmp_path / "test_policy.cedar"
        policy_file.write_text(policy_str)
        policy = Policy.from_file(str(policy_file))
        assert policy is not None
    
    def test_invalid_policy(self):
        """Test that invalid policies raise appropriate errors."""
        from cedar_py import Policy
        import pytest
        invalid_policy = """
        permit(
          principal == User::"alice",
          action == Action::"read",
          resource == Document::"doc123"
        )  // Missing semicolon
        """
        with pytest.raises(ValueError):
            Policy(invalid_policy)


class TestPolicySet:
    """Tests for the PolicySet class."""
    
    def test_empty_policy_set(self):
        """Test creating an empty PolicySet."""
        from cedar_py import PolicySet
        policy_set = PolicySet()
        assert policy_set is not None
        assert len(policy_set) == 0
    
    def test_add_policy(self):
        """Test adding a Policy to a PolicySet."""
        from cedar_py import Policy, PolicySet
        policy_str = """
        permit(
          principal == User::"alice",
          action == Action::"read",
          resource == Document::"doc123"
        );
        """
        policy = Policy(policy_str)
        policy_set = PolicySet()
        policy_set.add(policy)
        assert len(policy_set) == 1
    
    def test_multiple_policies(self):
        """Test adding multiple policies to a PolicySet."""
        from cedar_py import Policy, PolicySet
        # Test that we can create separate policy sets with different policies
        policy1 = Policy("""
        @id("policy1")
        permit(
          principal == User::"alice",
          action == Action::"read",
          resource == Document::"doc123"
        );
        """)
        policy2 = Policy("""
        @id("policy2")
        permit(
          principal == User::"bob",
          action == Action::"write",
          resource == Document::"doc456"
        );
        """)
        policy_set1 = PolicySet()
        policy_set1.add(policy1)
        policy_set2 = PolicySet()
        policy_set2.add(policy2)
        # Verify that each policy set has the right policy
        assert len(policy_set1) == 1
        assert len(policy_set2) == 1
        assert "policy1" in policy_set1.policies
        assert "policy2" in policy_set2.policies
