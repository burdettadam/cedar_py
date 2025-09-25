"""
Engine module for handling Cedar authorization decisions with intelligent caching
"""

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

from ._rust_importer import RustCedarAuthorizer as CedarAuthorizer
from .models import Action, Context, Entity, Principal, Resource
from .policy import Policy, PolicySet

LOGGER = logging.getLogger(__name__)


@dataclass
class AuthorizationResponse:
    """
    Represents a detailed authorization response.
    """

    allowed: bool
    decision: List[str]
    errors: List[str]


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


@dataclass
class CacheConfig:
    """Configuration for intelligent caching in Engine."""

    enabled: bool = False
    max_size: int = 10000
    default_ttl: float = 300.0  # 5 minutes
    enable_policy_aware_invalidation: bool = True

    @classmethod
    def create_enabled(cls, max_size: int = 10000, ttl: float = 300.0) -> "CacheConfig":
        """Create an enabled cache configuration."""
        return cls(enabled=True, max_size=max_size, default_ttl=ttl)


class Engine:
    """
    The main Cedar authorization engine with optional intelligent caching.

    Args:
        policy_set (Optional[Union[Policy, PolicySet]]): A Policy or PolicySet containing the policies. If None, an empty PolicySet is used.
        schema (Optional[Dict[str, Any]]): A JSON object representing the schema.
        entities (Optional[Dict[str, Any]]): A dictionary of entities.
        validate (bool): Whether to validate the schema and policies.
        cache_config (Optional[CacheConfig]): Cache configuration. If None, caching is disabled.
    """

    def __init__(
        self,
        policy_set: Optional[Union[Policy, PolicySet]] = None,
        schema: Optional[Dict[str, Any]] = None,
        entities: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        cache_config: Optional[CacheConfig] = None,
    ):
        """
        Initialize the Engine.
        """
        # Convert a single Policy to a PolicySet if needed
        if policy_set is None:
            self._policy_set = PolicySet()
        elif isinstance(policy_set, Policy):
            self._policy_set = PolicySet()
            self._policy_set.add(policy_set)
        else:
            self._policy_set = policy_set

        self._schema = schema
        self._entities = entities or {}
        self._authorizer = CedarAuthorizer()

        # Initialize caching if enabled
        self._cache_config = cache_config
        if cache_config and cache_config.enabled:
            self._init_cache()
        else:
            self._cache: Optional[OrderedDict[str, CacheEntry]] = None
            self._cache_lock: Optional[threading.RLock] = None
            self._cache_stats: Optional[CacheStats] = None
            self._current_policies_hash: Optional[str] = None

        if validate and schema:
            # TODO: Implement schema validation if required by the Rust bindings
            pass

    def _init_cache(self):
        """Initialize cache structures."""
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._cache_lock = threading.RLock()
        self._cache_stats = CacheStats()
        self._current_policies_hash = self._compute_policies_hash()
        if self._cache_config:  # Type guard
            LOGGER.info(
                f"Cache initialized with max_size: {self._cache_config.max_size}"
            )

    def _compute_policies_hash(self) -> str:
        """Compute hash of current policy set for cache invalidation."""
        policy_text = str(self._policy_set)
        return hashlib.md5(policy_text.encode()).hexdigest()

    def _generate_cache_key(
        self,
        principal: Principal,
        action: Action,
        resource: Resource,
        context: Optional[Context],
        entities: Optional[Dict[str, Any]],
    ) -> str:
        """Generate deterministic cache key."""
        import hashlib

        key_parts = [str(principal.uid), str(action.uid), str(resource.uid)]

        if context and context.data:
            # Sort context data for consistent key generation
            context_str = str(sorted(context.data.items()))
            key_parts.append(context_str)

        if entities:
            # Sort entities for consistent key generation
            entities_str = str(sorted(entities.items()))
            key_parts.append(entities_str)

        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _get_cached_result(self, cache_key: str) -> Optional[bool]:
        """Get cached result if valid."""
        if (
            self._cache is None
            or not self._cache_config
            or not self._cache_config.enabled
            or self._cache_lock is None
            or self._cache_stats is None
            or self._current_policies_hash is None
        ):
            return None

        with self._cache_lock:
            start_time = time.perf_counter()

            if cache_key in self._cache:
                entry = self._cache[cache_key]

                # Check if entry is still valid
                if not entry.is_expired() and entry.is_valid_for_policies(
                    self._current_policies_hash
                ):
                    # Move to end (mark as recently used)
                    self._cache.move_to_end(cache_key)
                    entry.access_count += 1

                    self._cache_stats.hits += 1
                    self._cache_stats.total_requests += 1

                    lookup_time = (time.perf_counter() - start_time) * 1000
                    self._update_avg_lookup_time(lookup_time)

                    return entry.result
                else:
                    # Remove expired/invalid entry
                    del self._cache[cache_key]

            self._cache_stats.misses += 1
            self._cache_stats.total_requests += 1

            lookup_time = (time.perf_counter() - start_time) * 1000
            self._update_avg_lookup_time(lookup_time)

            return None

    def _cache_result(self, cache_key: str, result: bool, ttl: Optional[float] = None):
        """Store result in cache."""
        if (
            self._cache is None
            or not self._cache_config
            or not self._cache_config.enabled
            or self._cache_lock is None
            or self._cache_stats is None
            or self._current_policies_hash is None
        ):
            return

        with self._cache_lock:
            # Remove oldest entries if at capacity
            while len(self._cache) >= self._cache_config.max_size:
                oldest_key, _ = self._cache.popitem(last=False)
                self._cache_stats.evictions += 1
                LOGGER.debug(f"Evicted cache entry: {oldest_key}")

            effective_ttl = ttl or self._cache_config.default_ttl
            entry = CacheEntry(
                result=result,
                timestamp=time.time(),
                ttl=effective_ttl,
                policies_hash=self._current_policies_hash,
            )

            self._cache[cache_key] = entry
            LOGGER.debug(f"Cached authorization result for: {cache_key}")

    def _update_avg_lookup_time(self, lookup_time_ms: float):
        """Update running average of lookup time."""
        if not self._cache_stats:
            return

        if self._cache_stats.total_requests == 1:
            self._cache_stats.avg_lookup_time_ms = lookup_time_ms
        else:
            # Exponential moving average
            alpha = 0.1
            self._cache_stats.avg_lookup_time_ms = (
                alpha * lookup_time_ms
                + (1 - alpha) * self._cache_stats.avg_lookup_time_ms
            )

    def invalidate_cache(self):
        """Invalidate entire cache."""
        if (
            self._cache is None
            or not self._cache_config
            or not self._cache_config.enabled
            or self._cache_lock is None
        ):
            return

        with self._cache_lock:
            self._cache.clear()
            LOGGER.info("Cache cleared")

    def invalidate_policy_cache(self):
        """Invalidate cache when policies change."""
        if (
            self._cache is None
            or not self._cache_config
            or not self._cache_config.enabled
            or self._cache_lock is None
            or self._current_policies_hash is None
        ):
            return

        if self._cache_config.enable_policy_aware_invalidation:
            old_hash = self._current_policies_hash
            new_hash = self._compute_policies_hash()

            if old_hash != new_hash:
                with self._cache_lock:
                    keys_to_remove = [
                        key
                        for key, entry in self._cache.items()
                        if entry.policies_hash == old_hash
                    ]

                    for key in keys_to_remove:
                        del self._cache[key]

                self._current_policies_hash = new_hash
                LOGGER.info(
                    f"Policy change detected - invalidated {len(keys_to_remove)} cache entries"
                )

    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics."""
        if (
            self._cache is None
            or not self._cache_config
            or not self._cache_config.enabled
        ):
            return None

        if not self._cache_stats:
            return None

        return {
            "hit_rate": self._cache_stats.hit_rate,
            "miss_rate": self._cache_stats.miss_rate,
            "hits": self._cache_stats.hits,
            "misses": self._cache_stats.misses,
            "evictions": self._cache_stats.evictions,
            "total_requests": self._cache_stats.total_requests,
            "avg_lookup_time_ms": self._cache_stats.avg_lookup_time_ms,
            "current_cache_size": len(self._cache),
            "max_cache_size": self._cache_config.max_size,
        }

    def is_authorized(
        self,
        principal: Union[Principal, str],
        action: Union[Action, str],
        resource: Union[Resource, str],
        context: Optional[Context] = None,
        entities: Optional[Dict[str, Any]] = None,
        cache_ttl: Optional[float] = None,
    ) -> bool:
        """
        Check if a request is authorized.

        Args:
            principal (Union[Principal, str]): The principal entity or string identifier.
            action (Union[Action, str]): The action entity or string identifier.
            resource (Union[Resource, str]): The resource entity or string identifier.
            context (Optional[Context]): The context of the request.
            entities (Optional[Dict[str, Any]]): Additional entities to consider for this authorization check.
            cache_ttl (Optional[float]): Custom TTL for this specific cache entry.

        Returns:
            bool: True if the request is allowed, False otherwise.
        """
        # Convert string identifiers to model objects if needed
        if isinstance(principal, str):
            principal = Principal(uid=principal)
        if isinstance(action, str):
            action = Action(uid=action)
        if isinstance(resource, str):
            resource = Resource(uid=resource)

        # Try cache first if enabled
        if self._cache is not None:
            cache_key = self._generate_cache_key(
                principal, action, resource, context, entities
            )
            cached_result = self._get_cached_result(cache_key)
            if cached_result is not None:
                return cached_result

        # Prepare entities dict for serialization
        entities_dict = self._prepare_entities(principal, action, resource, entities)

        # Convert all entities to dicts for JSON serialization, handle dicts and model objects
        def entity_to_dict(e):
            return e.to_dict() if hasattr(e, "to_dict") else e

        entities_json = (
            json.dumps([entity_to_dict(e) for e in entities_dict.values()])
            if entities_dict
            else None
        )
        context_json = json.dumps(context.data) if context else None

        # Call the Rust authorizer
        result = self._authorizer.is_authorized(
            policy_set=self._policy_set.rust_policy_set,
            principal=principal.uid,
            action=action.uid,
            resource=resource.uid,
            context_json=context_json,
            entities_json=entities_json,
        )

        # Cache the result if caching is enabled
        if self._cache is not None:
            self._cache_result(cache_key, result, cache_ttl)

        return result

    def _prepare_entities(
        self,
        principal: Principal,
        action: Action,
        resource: Resource,
        extra_entities: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Prepare the entities dictionary for authorization."""
        entities_dict = {}

        # Add engine-level entities first
        if self._entities:
            entities_dict.update(self._entities)

        # Add request-specific entities, allowing override
        if extra_entities:
            entities_dict.update(extra_entities)

        # Add the main actors, ensuring they are in the dict
        for entity in [principal, action, resource]:
            self._add_entity_and_parents(entities_dict, entity)

        return entities_dict

    def _add_entity_and_parents(
        self, entities_dict: Dict[str, Any], entity: Entity
    ) -> None:
        """Recursively add an entity and its parents to the entities dictionary."""
        # Use a simple UID-based key for the dictionary
        if entity.uid not in entities_dict:
            entities_dict[entity.uid] = entity.to_dict()
            for parent in entity.parents:
                self._add_entity_and_parents(entities_dict, parent)

    def is_authorized_detailed(
        self,
        principal: Union[Principal, str],
        action: Union[Action, str],
        resource: Union[Resource, str],
        context: Optional[Context] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Check if a request is authorized and get a detailed response.

        Args:
            principal (Union[Principal, str]): The principal entity or string identifier.
            action (Union[Action, str]): The action entity or string identifier.
            resource (Union[Resource, str]): The resource entity or string identifier.
            context (Optional[Context]): The context of the request.
            entities (Optional[Dict[str, Any]]): Additional entities to consider for this authorization check.

        Returns:
            Tuple[bool, List[str], List[str]]: (allowed, policy_ids, errors)
        """
        # Convert string identifiers to model objects if needed
        if isinstance(principal, str):
            principal = Principal(uid=principal)
        if isinstance(action, str):
            action = Action(uid=action)
        if isinstance(resource, str):
            resource = Resource(uid=resource)

        # Prepare entities dict for serialization
        entities_dict = self._prepare_entities(principal, action, resource, entities)

        def entity_to_dict(e):
            return e.to_dict() if hasattr(e, "to_dict") else e

        entities_json = (
            json.dumps([entity_to_dict(e) for e in entities_dict.values()])
            if entities_dict
            else None
        )
        context_json = json.dumps(context.data) if context else None

        # Call the Rust authorizer
        return self._authorizer.is_authorized_detailed(
            policy_set=self._policy_set.rust_policy_set,
            principal=principal.uid,
            action=action.uid,
            resource=resource.uid,
            context_json=context_json,
            entities_json=entities_json,
        )

    def authorize(
        self,
        principal: Principal,
        action: Action,
        resource: Resource,
        context: Optional[Context] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> AuthorizationResponse:
        """
        Get a detailed authorization response.

        Args:
            principal (Principal): The principal entity.
            action (Action): The action entity.
            resource (Resource): The resource entity.
            context (Optional[Context]): The context of the request.
            entities (Optional[Dict[str, Any]]): Additional entities to consider for this authorization check.

        Returns:
            AuthorizationResponse: The detailed authorization response.
        """
        allowed, decision, errors = self.is_authorized_detailed(
            principal, action, resource, context, entities
        )
        return AuthorizationResponse(allowed, decision, errors)

    def add_policy(self, policy: Policy) -> None:
        """
        Add a policy to the engine's policy set.

        Args:
            policy (Policy): The policy to add.
        """
        self._policy_set.add(policy)

        # Invalidate cache when policies change
        self.invalidate_policy_cache()
