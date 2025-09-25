"""
Example 2: Async Task Management System
Demonstrates Cedar-Py async capabilities and advanced authorization patterns.
"""

import asyncio
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

from cedar_py import Policy, Engine
from cedar_py.engine import CacheConfig

# Data models
@dataclass 
class User:
    id: str
    name: str
    department: str
    role: str
    level: int = 1
    permissions: Set[str] = field(default_factory=set)

@dataclass
class Task:
    id: str
    title: str
    description: str
    assignee: str
    creator: str
    priority: str = "normal"  # low, normal, high, critical
    status: str = "open"      # open, in_progress, completed, closed
    department: str = "general"
    created_at: datetime = field(default_factory=datetime.now)
    due_date: Optional[datetime] = None

class TaskManager:
    """Async task management system with Cedar authorization."""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.tasks: Dict[str, Task] = {}
        self.cedar_engine = self._initialize_cedar()
        
    def _initialize_cedar(self) -> Engine:
        """Initialize Cedar engine with task management policies."""
        policies = """
        // Users can always read their own assigned tasks
        permit(
            principal,
            action == Action::"read", 
            resource
        ) when {
            resource.assignee == principal.id
        };
        
        // Users can read tasks they created
        permit(
            principal,
            action == Action::"read",
            resource
        ) when {
            resource.creator == principal.id
        };
        
        // Department members can read tasks in their department
        permit(
            principal,
            action == Action::"read",
            resource
        ) when {
            principal.department == resource.department
        };
        
        // Managers can read/update tasks in their department
        permit(
            principal,
            action in [Action::"read", Action::"update"],
            resource
        ) when {
            principal.role == "manager" &&
            principal.department == resource.department
        };
        
        // Task creators can update their tasks
        permit(
            principal,
            action == Action::"update",
            resource
        ) when {
            resource.creator == principal.id &&
            resource.status != "closed"
        };
        
        // Users can update tasks assigned to them
        permit(
            principal,
            action == Action::"update",
            resource
        ) when {
            resource.assignee == principal.id &&
            resource.status in ["open", "in_progress"]
        };
        
        // Admins can do everything
        permit(
            principal,
            action,
            resource
        ) when {
            principal.role == "admin"
        };
        
        // High-level users can create critical tasks
        permit(
            principal,
            action == Action::"create",
            resource
        ) when {
            resource.priority != "critical" || principal.level >= 3
        };
        
        // Managers and above can delete tasks in their department
        permit(
            principal,
            action == Action::"delete",
            resource
        ) when {
            principal.role in ["manager", "admin"] &&
            principal.department == resource.department
        };
        """
        
        policy = Policy(policies)
        cache_config = CacheConfig.create_enabled(max_size=500, ttl=600.0)
        return Engine(policy, cache_config=cache_config)
    
    async def add_user(self, user: User):
        """Add a user to the system."""
        self.users[user.id] = user
    
    async def create_task(self, task: Task, creator_id: str) -> bool:
        """Create a new task with authorization check."""
        creator = self.users.get(creator_id)
        if not creator:
            return False
        
        # Check if user is authorized to create this task
        authorized = await self._check_authorization_async(
            creator, "create", task
        )
        
        if authorized:
            self.tasks[task.id] = task
            return True
        return False
    
    async def get_tasks_for_user(self, user_id: str) -> List[Task]:
        """Get all tasks a user can read."""
        user = self.users.get(user_id)
        if not user:
            return []
        
        accessible_tasks = []
        
        # Check each task asynchronously
        authorization_tasks = []
        for task in self.tasks.values():
            auth_task = self._check_authorization_async(user, "read", task)
            authorization_tasks.append((task, auth_task))
        
        # Wait for all authorization checks
        for task, auth_future in authorization_tasks:
            try:
                if await auth_future:
                    accessible_tasks.append(task)
            except Exception:
                continue  # Skip tasks that cause authorization errors
        
        return accessible_tasks
    
    async def update_task(self, task_id: str, updates: Dict, user_id: str) -> bool:
        """Update a task with authorization check."""
        user = self.users.get(user_id)
        task = self.tasks.get(task_id)
        
        if not user or not task:
            return False
        
        # Check authorization
        authorized = await self._check_authorization_async(user, "update", task)
        if not authorized:
            return False
        
        # Apply updates
        for field, value in updates.items():
            if hasattr(task, field):
                setattr(task, field, value)
        
        return True
    
    async def delete_task(self, task_id: str, user_id: str) -> bool:
        """Delete a task with authorization check."""
        user = self.users.get(user_id)
        task = self.tasks.get(task_id)
        
        if not user or not task:
            return False
        
        authorized = await self._check_authorization_async(user, "delete", task)
        if authorized:
            del self.tasks[task_id]
            return True
        return False
    
    async def _check_authorization_async(self, user: User, action: str, task: Task) -> bool:
        """Perform async authorization check."""
        # Run authorization in executor to avoid blocking
        loop = asyncio.get_event_loop()
        
        def sync_auth():
            return self.cedar_engine.is_authorized(
                f'User::"{user.id}"',
                f'Action::"{action}"',
                f'Task::"{task.id}"',
                entities={
                    f'User::"{user.id}"': {
                        "uid": {"type": "User", "id": user.id},
                        "attrs": {
                            "name": user.name,
                            "department": user.department,
                            "role": user.role,
                            "level": user.level
                        },
                        "parents": []
                    },
                    f'Task::"{task.id}"': {
                        "uid": {"type": "Task", "id": task.id},
                        "attrs": {
                            "title": task.title,
                            "assignee": task.assignee,
                            "creator": task.creator,
                            "priority": task.priority,
                            "status": task.status,
                            "department": task.department
                        },
                        "parents": []
                    }
                }
            )
        
        return await loop.run_in_executor(None, sync_auth)
    
    async def get_cache_stats(self) -> Dict:
        """Get Cedar engine cache statistics."""
        return self.cedar_engine.get_cache_stats()

async def main():
    """Demonstrate async task management system."""
    print("🔄 Async Task Management System with Cedar-Py")
    print("=" * 50)
    
    # Initialize system
    task_manager = TaskManager()
    
    # Add users
    users = [
        User("alice", "Alice Johnson", "engineering", "engineer", 3),
        User("bob", "Bob Smith", "marketing", "manager", 2), 
        User("charlie", "Charlie Wilson", "engineering", "admin", 4),
        User("diana", "Diana Lee", "hr", "specialist", 1),
    ]
    
    for user in users:
        await task_manager.add_user(user)
    
    print(f"👥 Added {len(users)} users")
    
    # Create tasks
    tasks = [
        Task("task1", "Implement API", "Build REST API endpoints", "alice", "bob", "high", "open", "engineering"),
        Task("task2", "Write Documentation", "API documentation", "alice", "alice", "normal", "open", "engineering"),
        Task("task3", "Marketing Campaign", "Q4 campaign planning", "bob", "bob", "high", "in_progress", "marketing"),
        Task("task4", "HR Policy Update", "Update employee handbook", "diana", "charlie", "normal", "open", "hr"),
        Task("task5", "Critical Bug Fix", "Fix production issue", "alice", "charlie", "critical", "open", "engineering"),
    ]
    
    # Test task creation with authorization
    creation_results = []
    for task in tasks:
        result = await task_manager.create_task(task, task.creator)
        creation_results.append((task.title, result))
    
    print(f"\n📝 Task Creation Results:")
    for title, created in creation_results:
        status = "✅ Created" if created else "❌ Denied"
        print(f"   - {title}: {status}")
    
    # Test task access for different users
    print(f"\n🔍 Task Access by User:")
    for user in users:
        accessible_tasks = await task_manager.get_tasks_for_user(user.id)
        print(f"   - {user.name} ({user.role}): {len(accessible_tasks)} tasks accessible")
        for task in accessible_tasks[:2]:  # Show first 2 tasks
            print(f"     • {task.title} ({task.priority})")
    
    # Test task updates
    print(f"\n🔄 Task Update Tests:")
    
    # Alice tries to update her assigned task
    result = await task_manager.update_task("task1", {"status": "in_progress"}, "alice")
    print(f"   - Alice updating her task: {'✅ Success' if result else '❌ Denied'}")
    
    # Diana tries to update engineering task (should fail)
    result = await task_manager.update_task("task1", {"status": "completed"}, "diana")
    print(f"   - Diana updating engineering task: {'✅ Success' if result else '❌ Denied'}")
    
    # Bob (manager) updates marketing task
    result = await task_manager.update_task("task3", {"status": "completed"}, "bob")
    print(f"   - Bob (manager) updating marketing task: {'✅ Success' if result else '❌ Denied'}")
    
    # Test parallel authorization checks (performance demo)
    print(f"\n⚡ Performance Test: Parallel Authorization Checks")
    start_time = asyncio.get_event_loop().time()
    
    # Create multiple authorization check tasks
    auth_tasks = []
    for _ in range(100):  # 100 parallel checks
        for user in users[:2]:  # Alice and Bob
            for task in list(task_manager.tasks.values())[:3]:  # First 3 tasks
                auth_task = task_manager._check_authorization_async(user, "read", task)
                auth_tasks.append(auth_task)
    
    # Wait for all authorization checks
    results = await asyncio.gather(*auth_tasks, return_exceptions=True)
    authorized_count = sum(1 for r in results if r is True)
    
    end_time = asyncio.get_event_loop().time()
    
    print(f"   - Completed {len(auth_tasks)} authorization checks in {end_time - start_time:.3f}s")
    print(f"   - Authorization success rate: {authorized_count}/{len(auth_tasks)} ({authorized_count/len(auth_tasks):.1%})")
    
    # Show cache performance
    cache_stats = await task_manager.get_cache_stats()
    print(f"\n📊 Cache Performance:")
    print(f"   - Hit rate: {cache_stats['hit_rate']:.1%}")
    print(f"   - Total requests: {cache_stats['total_requests']}")
    print(f"   - Average lookup time: {cache_stats['avg_lookup_time_ms']:.3f}ms")
    
    print(f"\n🎉 Async task management demo completed!")

if __name__ == "__main__":
    asyncio.run(main())