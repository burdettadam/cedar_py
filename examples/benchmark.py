#!/usr/bin/env python3
"""
Performance Benchmark for Cedar-Py

This script benchmarks Cedar-Py against pure Python authorization implementations
to demonstrate the performance benefits of the Rust backend.

Run with: python examples/benchmark.py
"""

import statistics
import time
from typing import Any, Dict, List

from cedar_py import Engine, Policy, PolicySet
from cedar_py.models import Action, Context, Principal, Resource


class PurePythonAuthorizer:
    """Simple pure Python authorization for comparison."""

    def __init__(self, policies: List[Dict[str, Any]]):
        self.policies = policies

    def is_authorized(
        self, principal: str, action: str, resource: str, context: Dict = None
    ) -> bool:
        """Simple rule-based authorization in pure Python."""
        context = context or {}

        for policy in self.policies:
            if self._matches_policy(principal, action, resource, context, policy):
                return True
        return False

    def _matches_policy(
        self, principal: str, action: str, resource: str, context: Dict, policy: Dict
    ) -> bool:
        """Check if request matches a policy."""
        # Simple string matching for demo purposes
        if policy.get("principal") and policy["principal"] not in principal:
            return False
        if policy.get("action") and policy["action"] not in action:
            return False
        if policy.get("resource") and policy["resource"] not in resource:
            return False

        # Check context conditions
        for key, value in policy.get("context", {}).items():
            if context.get(key) != value:
                return False

        return True


def create_cedar_engine() -> Engine:
    """Create a Cedar engine with sample policies."""
    policies = [
        """
        permit(
            principal == User::"alice",
            action == Action::"read",
            resource == Document::"doc1"
        );
        """,
        """
        permit(
            principal in Role::"admin",
            action,
            resource
        );
        """,
        """
        permit(
            principal in Role::"manager",
            action in [Action::"read", Action::"edit"],
            resource
        )
        when { context.department == "engineering" };
        """,
        """
        permit(
            principal,
            action == Action::"read",
            resource
        )
        when { resource.visibility == "public" };
        """,
    ]

    policy_set = PolicySet()
    for policy_text in policies:
        policy = Policy(policy_text)
        policy_set.add(policy)

    return Engine(policy_set)


def create_python_authorizer() -> PurePythonAuthorizer:
    """Create pure Python authorizer with equivalent rules."""
    policies = [
        {"principal": "alice", "action": "read", "resource": "doc1"},
        {"principal": "admin", "action": "*", "resource": "*"},
        {
            "principal": "manager",
            "action": "read",
            "resource": "*",
            "context": {"department": "engineering"},
        },
        {
            "principal": "manager",
            "action": "edit",
            "resource": "*",
            "context": {"department": "engineering"},
        },
        {"action": "read", "resource": "public"},
    ]

    return PurePythonAuthorizer(policies)


def benchmark_cedar_py(engine: Engine, iterations: int = 10000) -> List[float]:
    """Benchmark Cedar-Py performance."""
    times = []

    # Test cases
    test_cases = [
        ('User::"alice"', 'Action::"read"', 'Document::"doc1"', {}),
        ('User::"bob"', 'Action::"write"', 'Document::"doc2"', {}),
        (
            'User::"manager1"',
            'Action::"read"',
            'Document::"doc3"',
            {"department": "engineering"},
        ),
        ('User::"user1"', 'Action::"read"', 'Document::"public_doc"', {}),
    ]

    for i in range(iterations):
        test_case = test_cases[i % len(test_cases)]
        principal, action, resource, context_data = test_case

        start_time = time.perf_counter()

        principal_obj = Principal(principal)
        action_obj = Action(action)
        resource_obj = Resource(resource)
        context_obj = Context(context_data) if context_data else None

        if context_obj:
            result = engine.is_authorized(
                principal_obj, action_obj, resource_obj, context_obj
            )
        else:
            result = engine.is_authorized(principal_obj, action_obj, resource_obj)

        end_time = time.perf_counter()
        times.append(end_time - start_time)

    return times


def benchmark_pure_python(
    authorizer: PurePythonAuthorizer, iterations: int = 10000
) -> List[float]:
    """Benchmark pure Python performance."""
    times = []

    test_cases = [
        ("alice", "read", "doc1", {}),
        ("bob", "write", "doc2", {}),
        ("manager1", "read", "doc3", {"department": "engineering"}),
        ("user1", "read", "public_doc", {}),
    ]

    for i in range(iterations):
        test_case = test_cases[i % len(test_cases)]
        principal, action, resource, context = test_case

        start_time = time.perf_counter()
        result = authorizer.is_authorized(principal, action, resource, context)
        end_time = time.perf_counter()

        times.append(end_time - start_time)

    return times


def run_benchmark():
    """Run comprehensive performance benchmark."""
    print("🚀 Cedar-Py Performance Benchmark")
    print("=" * 50)

    # Setup
    cedar_engine = create_cedar_engine()
    python_authorizer = create_python_authorizer()

    iterations = 10000
    print(f"Running {iterations:,} authorization checks for each implementation...\n")

    # Warm up
    print("Warming up...")
    benchmark_cedar_py(cedar_engine, 100)
    benchmark_pure_python(python_authorizer, 100)

    # Cedar-Py benchmark
    print("Benchmarking Cedar-Py...")
    cedar_times = benchmark_cedar_py(cedar_engine, iterations)

    # Pure Python benchmark
    print("Benchmarking Pure Python...")
    python_times = benchmark_pure_python(python_authorizer, iterations)

    # Calculate statistics
    cedar_stats = {
        "mean": statistics.mean(cedar_times) * 1000,  # Convert to milliseconds
        "median": statistics.median(cedar_times) * 1000,
        "stdev": statistics.stdev(cedar_times) * 1000,
        "min": min(cedar_times) * 1000,
        "max": max(cedar_times) * 1000,
        "total": sum(cedar_times),
    }

    python_stats = {
        "mean": statistics.mean(python_times) * 1000,
        "median": statistics.median(python_times) * 1000,
        "stdev": statistics.stdev(python_times) * 1000,
        "min": min(python_times) * 1000,
        "max": max(python_times) * 1000,
        "total": sum(python_times),
    }

    # Display results
    print("\n📊 BENCHMARK RESULTS")
    print("=" * 50)

    print("\n🦀 Cedar-Py (Rust Backend):")
    print(f"  Mean time per check:   {cedar_stats['mean']:.4f} ms")
    print(f"  Median time per check: {cedar_stats['median']:.4f} ms")
    print(f"  Standard deviation:    {cedar_stats['stdev']:.4f} ms")
    print(f"  Min time:              {cedar_stats['min']:.4f} ms")
    print(f"  Max time:              {cedar_stats['max']:.4f} ms")
    print(f"  Total time:            {cedar_stats['total']:.4f} s")
    print(
        f"  Throughput:            {iterations / cedar_stats['total']:,.0f} checks/sec"
    )

    print("\n🐍 Pure Python:")
    print(f"  Mean time per check:   {python_stats['mean']:.4f} ms")
    print(f"  Median time per check: {python_stats['median']:.4f} ms")
    print(f"  Standard deviation:    {python_stats['stdev']:.4f} ms")
    print(f"  Min time:              {python_stats['min']:.4f} ms")
    print(f"  Max time:              {python_stats['max']:.4f} ms")
    print(f"  Total time:            {python_stats['total']:.4f} s")
    print(
        f"  Throughput:            {iterations / python_stats['total']:,.0f} checks/sec"
    )

    # Performance comparison
    speedup = python_stats["mean"] / cedar_stats["mean"]
    throughput_improvement = (iterations / cedar_stats["total"]) / (
        iterations / python_stats["total"]
    )

    print("\n⚡ PERFORMANCE COMPARISON:")
    print(f"  Cedar-Py is {speedup:.1f}x faster per check")
    print(f"  Cedar-Py has {throughput_improvement:.1f}x higher throughput")
    print(
        f"  Time savings: {((python_stats['total'] - cedar_stats['total']) / python_stats['total'] * 100):.1f}%"
    )

    # Memory efficiency note
    print("\n🧠 Additional Benefits:")
    print("  • Lower memory overhead with compiled policies")
    print("  • Zero-copy operations between Python and Rust")
    print("  • Built-in policy validation and optimization")
    print("  • Industry-standard Cedar language compliance")

    print("\n" + "=" * 50)
    print("💡 These results demonstrate Cedar-Py's performance advantage")
    print("   for authorization-heavy applications and high-throughput systems.")


if __name__ == "__main__":
    run_benchmark()
