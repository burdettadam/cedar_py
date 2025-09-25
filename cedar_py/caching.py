"""
Quick Win #2: Intelligent Caching Layer for Cedar-Py
High-performance caching with smart invalidation and optimization.
"""

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from cedar_py import Engine
from cedar_py.models import Action, Context, Principal, Resource

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache performance statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_requests: int = 0
    avg_lookup_time_ms: float = 0.0

    @property
    def hit_rate(self) -> float:
        return self.hits / max(self.total_requests, 1)

    @property
    def miss_rate(self) -> float:
        return self.misses / max(self.total_requests, 1)


@dataclass
class CacheEntry:
    """Individual cache entry with metadata."""

    result: bool
    timestamp: float
    ttl: float
    access_count: int = 0
    policies_hash: Optional[str] = None

    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl

    def is_valid_for_policies(self, current_policies_hash: str) -> bool:
        return self.policies_hash == current_policies_hash


class LRUCache:
    """Thread-safe LRU cache implementation."""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats()

    def get(self, key: str, policies_hash: str) -> Optional[bool]:
        """Get cached result if valid."""
        with self._lock:
            start_time = time.perf_counter()

            if key in self._cache:
                entry = self._cache[key]

                # Check if entry is still valid
                if not entry.is_expired() and entry.is_valid_for_policies(
                    policies_hash
                ):
                    # Move to end (mark as recently used)
                    self._cache.move_to_end(key)
                    entry.access_count += 1

                    self._stats.hits += 1
                    self._stats.total_requests += 1

                    lookup_time = (time.perf_counter() - start_time) * 1000
                    self._update_avg_lookup_time(lookup_time)

                    return entry.result
                else:
                    # Remove expired/invalid entry
                    del self._cache[key]

            self._stats.misses += 1
            self._stats.total_requests += 1

            lookup_time = (time.perf_counter() - start_time) * 1000
            self._update_avg_lookup_time(lookup_time)

            return None

    def put(self, key: str, result: bool, ttl: float, policies_hash: str):
        """Store result in cache."""
        with self._lock:
            # Remove oldest entries if at capacity
            while len(self._cache) >= self.max_size:
                oldest_key, _ = self._cache.popitem(last=False)
                self._stats.evictions += 1
                logger.debug(f"Evicted cache entry: {oldest_key}")

            entry = CacheEntry(
                result=result,
                timestamp=time.time(),
                ttl=ttl,
                policies_hash=policies_hash,
            )

            self._cache[key] = entry
            logger.debug(f"Cached authorization result for: {key}")

    def invalidate_by_policy_hash(self, old_policies_hash: str):
        """Invalidate all entries with specific policy hash."""
        with self._lock:
            keys_to_remove = [
                key
                for key, entry in self._cache.items()
                if entry.policies_hash == old_policies_hash
            ]

            for key in keys_to_remove:
                del self._cache[key]

            logger.info(
                f"Invalidated {len(keys_to_remove)} cache entries due to policy change"
            )

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    def stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                total_requests=self._stats.total_requests,
                avg_lookup_time_ms=self._stats.avg_lookup_time_ms,
            )

    def _update_avg_lookup_time(self, lookup_time_ms: float):
        """Update running average of lookup time."""
        if self._stats.total_requests == 1:
            self._stats.avg_lookup_time_ms = lookup_time_ms
        else:
            # Exponential moving average
            alpha = 0.1
            self._stats.avg_lookup_time_ms = (
                alpha * lookup_time_ms + (1 - alpha) * self._stats.avg_lookup_time_ms
            )


class IntelligentCacheConfig:
    """Configuration for intelligent caching."""

    def __init__(
        self,
        max_size: int = 10000,
        default_ttl: float = 300.0,  # 5 minutes
        enable_policy_aware_invalidation: bool = True,
        enable_hot_path_optimization: bool = True,
        enable_background_refresh: bool = False,
        background_refresh_threshold: float = 0.8,  # Refresh when 80% of TTL elapsed
        max_workers: int = 4,
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.enable_policy_aware_invalidation = enable_policy_aware_invalidation
        self.enable_hot_path_optimization = enable_hot_path_optimization
        self.enable_background_refresh = enable_background_refresh
        self.background_refresh_threshold = background_refresh_threshold
        self.max_workers = max_workers


class CachedEngine:
    """
    Intelligent caching wrapper for Cedar Engine.

    Features:
    - LRU cache with configurable size and TTL
    - Policy-aware cache invalidation
    - Hot path optimization
    - Background cache refresh
    - Comprehensive metrics and monitoring
    """

    def __init__(self, engine: Engine, config: Optional[IntelligentCacheConfig] = None):
        self.engine = engine
        self.config = config or IntelligentCacheConfig()
        self.cache = LRUCache(self.config.max_size)

        # Track policy changes for smart invalidation
        self.current_policies_hash = self._compute_policies_hash()

        # Hot path optimization
        self.hot_queries: Dict[str, int] = {}  # query -> frequency
        self.hot_threshold = 10  # Queries with frequency > 10 are "hot"

        # Background refresh
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        self.refresh_queue: Set[str] = set()

        logger.info(f"Initialized CachedEngine with cache size: {self.config.max_size}")

    def is_authorized(
        self,
        principal,
        action,
        resource,
        context: Optional[Context] = None,
        entities: Optional[Dict[str, Any]] = None,
        cache_ttl: Optional[float] = None,
    ) -> bool:
        """
        Cached authorization check with intelligent caching.
        """
        # Generate cache key
        cache_key = self._generate_cache_key(
            principal, action, resource, context, entities
        )

        # Track query frequency for hot path optimization
        self._track_query_frequency(cache_key)

        # Check cache first
        current_policies_hash = self._compute_policies_hash()
        cached_result = self.cache.get(cache_key, current_policies_hash)

        if cached_result is not None:
            logger.debug(f"Cache HIT for: {cache_key}")

            # Background refresh for hot queries near expiration
            if (
                self.config.enable_background_refresh
                and self._should_background_refresh(cache_key)
            ):
                self._schedule_background_refresh(
                    cache_key, principal, action, resource, context, entities
                )

            return cached_result

        # Cache miss - compute result
        logger.debug(f"Cache MISS for: {cache_key}")
        start_time = time.perf_counter()

        result = self.engine.is_authorized(
            principal, action, resource, context, entities
        )

        compute_time = (time.perf_counter() - start_time) * 1000
        logger.debug(f"Authorization computed in {compute_time:.2f}ms")

        # Cache the result
        ttl = cache_ttl or self._get_adaptive_ttl(cache_key)
        self.cache.put(cache_key, result, ttl, current_policies_hash)

        return result

    def invalidate_policy_cache(self):
        """Invalidate cache when policies change."""
        if self.config.enable_policy_aware_invalidation:
            old_hash = self.current_policies_hash
            new_hash = self._compute_policies_hash()

            if old_hash != new_hash:
                self.cache.invalidate_by_policy_hash(old_hash)
                self.current_policies_hash = new_hash
                logger.info(
                    "Policy change detected - invalidated related cache entries"
                )

    def warm_cache(
        self, queries: List[Tuple[str, str, str, Optional[Dict], Optional[Dict]]]
    ):
        """Pre-warm cache with common queries."""
        logger.info(f"Warming cache with {len(queries)} queries...")

        for principal, action, resource, context_data, entities in queries:
            context = Context(context_data) if context_data else None
            try:
                self.is_authorized(principal, action, resource, context, entities)
            except Exception as e:
                logger.warning(f"Failed to warm cache for query: {e}")

        logger.info("Cache warming completed")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = self.cache.stats()

        return {
            "cache_performance": {
                "hit_rate": stats.hit_rate,
                "miss_rate": stats.miss_rate,
                "hits": stats.hits,
                "misses": stats.misses,
                "evictions": stats.evictions,
                "total_requests": stats.total_requests,
                "avg_lookup_time_ms": stats.avg_lookup_time_ms,
            },
            "hot_queries": {
                "total_hot_queries": len(
                    [
                        q
                        for q, freq in self.hot_queries.items()
                        if freq >= self.hot_threshold
                    ]
                ),
                "top_queries": sorted(
                    self.hot_queries.items(), key=lambda x: x[1], reverse=True
                )[:10],
            },
            "cache_config": {
                "max_size": self.config.max_size,
                "default_ttl": self.config.default_ttl,
                "policy_aware_invalidation": self.config.enable_policy_aware_invalidation,
                "background_refresh": self.config.enable_background_refresh,
            },
            "current_cache_size": len(self.cache._cache),
        }

    def get_optimization_suggestions(self) -> List[str]:
        """Get suggestions for cache optimization."""
        suggestions = []
        stats = self.cache.stats()

        if stats.hit_rate < 0.7:
            suggestions.append("Consider increasing cache size - hit rate is below 70%")

        if stats.avg_lookup_time_ms > 1.0:
            suggestions.append(
                "Cache lookup time is high - consider optimizing cache key generation"
            )

        hot_queries_count = len(
            [q for q, freq in self.hot_queries.items() if freq >= self.hot_threshold]
        )

        if hot_queries_count > self.config.max_size * 0.5:
            suggestions.append(
                "Many hot queries detected - consider increasing cache size"
            )

        if stats.evictions > stats.hits * 0.1:
            suggestions.append(
                "High eviction rate - consider increasing cache size or reducing TTL"
            )

        return suggestions

    def _generate_cache_key(
        self,
        principal,
        action,
        resource,
        context: Optional[Context],
        entities: Optional[Dict[str, Any]],
    ) -> str:
        """Generate deterministic cache key."""
        key_parts = [str(principal), str(action), str(resource)]

        if context:
            # Sort context data for consistent key generation
            context_str = str(sorted(context.data.items()) if context.data else "")
            key_parts.append(context_str)

        if entities:
            # Sort entities for consistent key generation
            entities_str = str(sorted(entities.items()))
            key_parts.append(entities_str)

        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]

    def _compute_policies_hash(self) -> str:
        """Compute hash of current policies for invalidation."""
        try:
            # This is a simplified approach - in practice, you'd want to hash
            # the actual policy content or use policy version numbers
            policies_str = str(self.engine._policy_set._policies.keys())
            return hashlib.sha256(policies_str.encode()).hexdigest()[:16]
        except Exception:
            return str(time.time())  # Fallback to timestamp

    def _track_query_frequency(self, cache_key: str):
        """Track query frequency for hot path optimization."""
        if self.config.enable_hot_path_optimization:
            self.hot_queries[cache_key] = self.hot_queries.get(cache_key, 0) + 1

    def _get_adaptive_ttl(self, cache_key: str) -> float:
        """Get adaptive TTL based on query frequency."""
        base_ttl = self.config.default_ttl

        if not self.config.enable_hot_path_optimization:
            return base_ttl

        frequency = self.hot_queries.get(cache_key, 0)

        if frequency >= self.hot_threshold:
            # Hot queries get longer TTL
            return base_ttl * 2
        elif frequency >= self.hot_threshold // 2:
            # Warm queries get slightly longer TTL
            return base_ttl * 1.5
        else:
            return base_ttl

    def _should_background_refresh(self, cache_key: str) -> bool:
        """Determine if query should be background refreshed."""
        if not self.config.enable_background_refresh:
            return False

        frequency = self.hot_queries.get(cache_key, 0)
        return frequency >= self.hot_threshold and cache_key not in self.refresh_queue

    def _schedule_background_refresh(
        self, cache_key, principal, action, resource, context, entities
    ):
        """Schedule background refresh for hot query."""
        if cache_key in self.refresh_queue:
            return

        self.refresh_queue.add(cache_key)

        def refresh_task():
            try:
                # Recompute and cache result
                result = self.engine.is_authorized(
                    principal, action, resource, context, entities
                )
                ttl = self._get_adaptive_ttl(cache_key)
                self.cache.put(cache_key, result, ttl, self.current_policies_hash)
                logger.debug(f"Background refreshed cache for: {cache_key}")
            except Exception as e:
                logger.error(f"Background refresh failed for {cache_key}: {e}")
            finally:
                self.refresh_queue.discard(cache_key)

        self.executor.submit(refresh_task)


# Usage Example
def create_cached_engine(engine: Engine) -> CachedEngine:
    """Create a high-performance cached engine."""
    config = IntelligentCacheConfig(
        max_size=50000,  # 50k cached decisions
        default_ttl=600,  # 10 minutes default
        enable_policy_aware_invalidation=True,
        enable_hot_path_optimization=True,
        enable_background_refresh=True,
    )

    cached_engine = CachedEngine(engine, config)

    # Pre-warm with common queries
    common_queries = [
        ("User::alice", "Action::read", "Document::public", None, None),
        ("User::admin", "Action::write", "Document::any", {"role": "admin"}, None),
    ]
    cached_engine.warm_cache(common_queries)

    return cached_engine


# Example integration with existing code
"""
# Before (basic engine)
engine = Engine(policy_set)
result = engine.is_authorized(principal, action, resource)

# After (cached engine with intelligence)
cached_engine = create_cached_engine(engine)
result = cached_engine.is_authorized(principal, action, resource)

# Monitor performance
stats = cached_engine.get_cache_stats()
print(f"Cache hit rate: {stats['cache_performance']['hit_rate']:.2%}")
print(f"Average lookup time: {stats['cache_performance']['avg_lookup_time_ms']:.2f}ms")

# Get optimization suggestions
suggestions = cached_engine.get_optimization_suggestions()
for suggestion in suggestions:
    print(f"💡 {suggestion}")
"""
