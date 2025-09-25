"""
Example 3: Simple Authorization System
Demonstrates Cedar-Py core capabilities with working single-line policies.
"""

import asyncio
from typing import Dict, List
from dataclasses import dataclass

from cedar_py import Policy, Engine
from cedar_py.engine import CacheConfig
from cedar_py import PolicyTestBuilder

@dataclass
class User:
    id: str
    name: str
    department: str
    role: str
    level: int = 1

@dataclass
class Resource:
    id: str
    name: str
    type: str
    owner: str
    department: str
    classification: str = "public"

class AuthorizationSystem:
    """Simple authorization system demonstrating Cedar-Py features."""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.resources: Dict[str, Resource] = {}
        self.engines = self._create_engines()
    
    def _create_engines(self) -> Dict[str, Engine]:
        """Create different engines for different scenarios."""
        engines = {}
        
        # Engine 1: Basic owner access
        owner_policy = Policy('permit(principal, action, resource) when { principal.id == resource.owner };')
        engines['owner'] = Engine(owner_policy)
        
        # Engine 2: Department access  
        dept_policy = Policy('permit(principal, action == Action::"read", resource) when { principal.department == resource.department };')
        engines['department'] = Engine(dept_policy)
        
        # Engine 3: Role-based access with caching
        role_policy = Policy('permit(principal, action, resource) when { principal.role == "admin" };')
        cache_config = CacheConfig.create_enabled(max_size=100, ttl=300.0)
        engines['admin'] = Engine(role_policy, cache_config=cache_config)
        
        # Engine 4: Public access
        public_policy = Policy('permit(principal, action == Action::"read", resource) when { resource.classification == "public" };')
        engines['public'] = Engine(public_policy)
        
        return engines
    
    def add_user(self, user: User):
        """Add a user to the system."""
        self.users[user.id] = user
    
    def add_resource(self, resource: Resource):
        """Add a resource to the system."""
        self.resources[resource.id] = resource
    
    def check_access(self, user_id: str, action: str, resource_id: str, engine_type: str = 'owner') -> bool:
        """Check if user can perform action on resource."""
        user = self.users.get(user_id)
        resource = self.resources.get(resource_id)
        engine = self.engines.get(engine_type)
        
        if not user or not resource or not engine:
            return False
        
        return engine.is_authorized(
            f'User::"{user_id}"',
            f'Action::"{action}"',
            f'Resource::"{resource_id}"',
            entities={
                f'User::"{user_id}"': {
                    "uid": {"type": "User", "id": user_id},
                    "attrs": {
                        "name": user.name,
                        "department": user.department,
                        "role": user.role,
                        "level": user.level
                    },
                    "parents": []
                },
                f'Resource::"{resource_id}"': {
                    "uid": {"type": "Resource", "id": resource_id},
                    "attrs": {
                        "name": resource.name,
                        "type": resource.type,
                        "owner": resource.owner,
                        "department": resource.department,
                        "classification": resource.classification
                    },
                    "parents": []
                }
            }
        )
    
    def get_accessible_resources(self, user_id: str, action: str) -> List[Resource]:
        """Get all resources a user can access with given action."""
        user = self.users.get(user_id)
        if not user:
            return []
        
        accessible = []
        for resource in self.resources.values():
            # Check multiple engines and allow if any permits
            access_granted = False
            for engine_type in self.engines:
                if self.check_access(user_id, action, resource.id, engine_type):
                    access_granted = True
                    break
            
            if access_granted:
                accessible.append(resource)
        
        return accessible
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics from admin engine."""
        return self.engines['admin'].get_cache_stats()

def run_authorization_demo():
    """Demonstrate authorization system capabilities."""
    print("🔐 Cedar-Py Authorization System Demo")
    print("=" * 40)
    
    # Initialize system
    auth_system = AuthorizationSystem()
    
    # Add users
    users = [
        User("alice", "Alice Johnson", "engineering", "engineer", 3),
        User("bob", "Bob Smith", "marketing", "manager", 2),
        User("charlie", "Charlie Wilson", "engineering", "admin", 4),
        User("diana", "Diana Lee", "hr", "specialist", 1),
    ]
    
    for user in users:
        auth_system.add_user(user)
    
    # Add resources
    resources = [
        Resource("doc1", "API Documentation", "document", "alice", "engineering", "internal"),
        Resource("doc2", "Marketing Plan", "document", "bob", "marketing", "confidential"),
        Resource("doc3", "Company Handbook", "document", "diana", "hr", "public"),
        Resource("code1", "Main Repository", "code", "alice", "engineering", "internal"),
        Resource("report1", "Sales Report", "report", "bob", "marketing", "confidential"),
    ]
    
    for resource in resources:
        auth_system.add_resource(resource)
    
    print(f"👥 Added {len(users)} users and {len(resources)} resources")
    print()
    
    # Test different authorization scenarios
    scenarios = [
        ("alice", "read", "doc1", "owner", "Alice reading her own doc"),
        ("bob", "read", "doc1", "owner", "Bob reading Alice's doc"),
        ("alice", "read", "code1", "department", "Alice reading engineering code"),
        ("diana", "read", "code1", "department", "Diana reading engineering code"),
        ("diana", "read", "doc3", "public", "Diana reading public handbook"),
        ("alice", "read", "doc3", "public", "Alice reading public handbook"),
        ("charlie", "write", "doc2", "admin", "Charlie (admin) writing marketing doc"),
        ("bob", "write", "doc2", "admin", "Bob writing marketing doc"),
    ]
    
    print("🧪 Authorization Test Results:")
    for user_id, action, resource_id, engine_type, description in scenarios:
        result = auth_system.check_access(user_id, action, resource_id, engine_type)
        status = "✅ ALLOWED" if result else "❌ DENIED"
        print(f"   - {description}: {status}")
    
    print()
    
    # Show accessible resources per user
    print("📋 Resource Access Summary:")
    for user in users:
        readable_resources = auth_system.get_accessible_resources(user.id, "read")
        print(f"   - {user.name}: {len(readable_resources)} readable resources")
        for resource in readable_resources[:2]:  # Show first 2
            print(f"     • {resource.name} ({resource.type})")
    
    print()
    
    # Performance test with caching
    print("⚡ Performance Test (Caching Demo):")
    
    # Make repeated authorization calls to test caching
    import time
    start_time = time.time()
    
    for _ in range(100):
        auth_system.check_access("charlie", "write", "doc2", "admin")
    
    end_time = time.time()
    
    cache_stats = auth_system.get_cache_stats()
    print(f"   - 100 authorization checks completed in {end_time - start_time:.3f}s")
    print(f"   - Cache hit rate: {cache_stats.get('hit_rate', 0):.1%}")
    print(f"   - Average lookup time: {cache_stats.get('avg_lookup_time_ms', 0):.3f}ms")
    
    print()

def run_testing_framework_demo():
    """Demonstrate testing framework capabilities."""
    print("🧪 Cedar-Py Testing Framework Demo")
    print("=" * 35)
    
    # Create test scenarios using PolicyTestBuilder
    scenarios = (PolicyTestBuilder()
                 .given_user("alice", department="engineering", role="engineer")
                 .when_accessing("read", "engineering_docs")
                 .should_be_allowed("Engineers can read engineering docs")
                 
                 .given_user("bob", department="marketing", role="manager")  
                 .when_accessing("read", "engineering_docs")
                 .should_be_denied("Marketing cannot read engineering docs")
                 
                 .given_user("charlie", department="engineering", role="admin")
                 .when_accessing("write", "any_resource") 
                 .should_be_allowed("Admins can write anything")
                 
                 .given_user("diana", department="hr", role="specialist")
                 .when_accessing("read", "public_handbook")
                 .should_be_allowed("Anyone can read public resources")
                 
                 .build_scenarios())
    
    print(f"📝 Built {len(scenarios)} test scenarios:")
    for i, scenario in enumerate(scenarios, 1):
        expected = "ALLOW" if scenario.expected_result else "DENY"
        print(f"   {i}. {scenario.description}: expect {expected}")
        print(f"      Principal: {scenario.principal}")
        print(f"      Action: {scenario.action}")  
        print(f"      Resource: {scenario.resource}")
        print()
    
    print("✅ Testing framework scenarios created successfully!")
    print()

def main():
    """Run all demos."""
    run_authorization_demo()
    run_testing_framework_demo()
    
    print("🎉 All demos completed successfully!")
    print("\n🚀 Cedar-Py Features Demonstrated:")
    print("   • Multiple policy engines")
    print("   • Entity-based authorization") 
    print("   • Intelligent caching")
    print("   • Performance optimization")
    print("   • Testing framework")
    print("   • Fluent API patterns")

if __name__ == "__main__":
    main()