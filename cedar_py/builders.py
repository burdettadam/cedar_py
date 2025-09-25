"""
Builder patterns for Cedar-Py components - Fluent API for complex initialization
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from .engine import Engine
from .errors import EngineInitializationError, PolicyParseError
from .models import Action, Context, Entity, Principal, Resource
from .policy import Policy, PolicySet

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Configuration for caching behavior"""

    enabled: bool = True
    policy_cache_size: int = 1000
    decision_cache_size: int = 5000
    decision_ttl_seconds: int = 300  # 5 minutes
    background_refresh: bool = False


@dataclass
class ValidationConfig:
    """Configuration for validation behavior"""

    enabled: bool = True
    strict_mode: bool = False
    validate_on_load: bool = True
    validate_on_update: bool = True


@dataclass
class LoggingConfig:
    """Configuration for logging and observability"""

    enabled: bool = True
    level: str = "INFO"
    structured: bool = True
    include_context: bool = True
    audit_enabled: bool = False


class PolicyBuilder:
    """
    Fluent builder for Policy objects with validation and error handling.

    Example:
        policy = (PolicyBuilder()
            .from_cedar_source(policy_text)
            .with_id("my_policy")
            .with_validation()
            .build())
    """

    def __init__(self):
        self._policy_data: Optional[str] = None
        self._policy_id: Optional[str] = None
        self._validate: bool = True
        self._metadata: Dict[str, Any] = {}

    def from_cedar_source(self, source: str) -> "PolicyBuilder":
        """Initialize from Cedar policy source code"""
        self._policy_data = source.strip()
        return self

    def from_cedar_json(self, json_data: Union[str, Dict[str, Any]]) -> "PolicyBuilder":
        """Initialize from Cedar JSON policy format"""
        if isinstance(json_data, dict):
            import json

            self._policy_data = json.dumps(json_data)
        else:
            self._policy_data = json_data
        return self

    def from_file(self, file_path: Union[str, Path]) -> "PolicyBuilder":
        """Load policy from file"""
        path = Path(file_path)
        if not path.exists():
            raise PolicyParseError(
                policy_text="",
                context={"file_path": str(file_path)},
                cause=FileNotFoundError(f"Policy file not found: {file_path}"),
            )

        try:
            self._policy_data = path.read_text(encoding="utf-8")
            return self
        except Exception as e:
            raise PolicyParseError(
                policy_text="", context={"file_path": str(file_path)}, cause=e
            )

    def with_id(self, policy_id: str) -> "PolicyBuilder":
        """Set explicit policy ID"""
        self._policy_id = policy_id
        return self

    def with_metadata(self, **metadata: Any) -> "PolicyBuilder":
        """Add metadata to the policy"""
        self._metadata.update(metadata)
        return self

    def without_validation(self) -> "PolicyBuilder":
        """Disable validation during policy creation"""
        self._validate = False
        return self

    def with_validation(self) -> "PolicyBuilder":
        """Enable validation during policy creation (default)"""
        self._validate = True
        return self

    def build(self) -> Policy:
        """Build the Policy object"""
        if not self._policy_data:
            raise PolicyParseError(
                policy_text="", context={"builder_state": "No policy data provided"}
            )

        try:
            policy = Policy(self._policy_data)

            # Apply explicit ID if provided
            if self._policy_id:
                policy._id = self._policy_id

            # Add metadata (simplified approach)
            setattr(policy, "_builder_metadata", self._metadata)

            logger.info(
                "Policy created via builder",
                extra={"policy_id": policy.id, "validation_enabled": self._validate},
            )

            return policy

        except Exception as e:
            raise PolicyParseError(
                policy_text=self._policy_data[:200] + "..."
                if len(self._policy_data) > 200
                else self._policy_data,
                cause=e,
            )


class EngineBuilder:
    """
    Fluent builder for Engine objects with advanced configuration.

    Example:
        engine = (EngineBuilder()
            .with_policies(policy_set)
            .with_schema_validation(schema)
            .with_caching(CacheConfig(ttl=300))
            .with_logging(LoggingConfig(audit_enabled=True))
            .build())
    """

    def __init__(self):
        self._policy_set: Optional[PolicySet] = None
        self._schema: Optional[Dict[str, Any]] = None
        self._entities: Dict[str, Any] = {}
        self._cache_config: Optional[CacheConfig] = None
        self._validation_config = ValidationConfig()
        self._logging_config = LoggingConfig()
        self._middleware: List[Callable] = []

    def with_policy(self, policy: Policy) -> "EngineBuilder":
        """Add a single policy"""
        if self._policy_set is None:
            self._policy_set = PolicySet()
        self._policy_set.add(policy)
        return self

    def with_policies(
        self, policy_set: Union[PolicySet, List[Policy]]
    ) -> "EngineBuilder":
        """Add a policy set or list of policies"""
        if isinstance(policy_set, list):
            self._policy_set = PolicySet()
            for policy in policy_set:
                self._policy_set.add(policy)
        else:
            self._policy_set = policy_set
        return self

    def with_policies_from_directory(
        self, directory: Union[str, Path]
    ) -> "EngineBuilder":
        """Load all policies from a directory"""
        dir_path = Path(directory)
        if not dir_path.exists():
            raise EngineInitializationError(
                reason=f"Policies directory not found: {directory}",
                config={"directory": str(directory)},
            )

        if self._policy_set is None:
            self._policy_set = PolicySet()

        policy_files = list(dir_path.glob("*.cedar")) + list(dir_path.glob("*.json"))

        for policy_file in policy_files:
            try:
                policy = PolicyBuilder().from_file(policy_file).build()
                self._policy_set.add(policy)
                logger.debug(f"Loaded policy from {policy_file}")
            except Exception as e:
                logger.warning(f"Failed to load policy from {policy_file}: {e}")
                if self._validation_config.strict_mode:
                    raise

        return self

    def with_schema(self, schema: Dict[str, Any]) -> "EngineBuilder":
        """Add schema for validation"""
        self._schema = schema
        return self

    def with_schema_from_file(self, schema_file: Union[str, Path]) -> "EngineBuilder":
        """Load schema from file"""
        path = Path(schema_file)
        try:
            import json

            self._schema = json.loads(path.read_text(encoding="utf-8"))
            return self
        except Exception as e:
            raise EngineInitializationError(
                reason=f"Failed to load schema from {schema_file}",
                config={"schema_file": str(schema_file)},
                cause=e,
            )

    def with_entities(self, entities: Dict[str, Any]) -> "EngineBuilder":
        """Add entity data"""
        self._entities.update(entities)
        return self

    def with_entity(self, entity: Entity) -> "EngineBuilder":
        """Add a single entity"""
        self._entities[entity.uid] = entity
        return self

    def with_caching(self, config: Optional[CacheConfig] = None) -> "EngineBuilder":
        """Enable caching with optional configuration"""
        self._cache_config = config or CacheConfig()
        return self

    def without_caching(self) -> "EngineBuilder":
        """Disable caching"""
        self._cache_config = CacheConfig(enabled=False)
        return self

    def with_validation(
        self, config: Optional[ValidationConfig] = None
    ) -> "EngineBuilder":
        """Configure validation behavior"""
        self._validation_config = config or ValidationConfig()
        return self

    def with_strict_validation(self) -> "EngineBuilder":
        """Enable strict validation mode"""
        self._validation_config.strict_mode = True
        return self

    def without_validation(self) -> "EngineBuilder":
        """Disable validation"""
        self._validation_config.enabled = False
        return self

    def with_logging(self, config: Optional[LoggingConfig] = None) -> "EngineBuilder":
        """Configure logging behavior"""
        self._logging_config = config or LoggingConfig()
        return self

    def with_audit_logging(self) -> "EngineBuilder":
        """Enable audit logging"""
        self._logging_config.audit_enabled = True
        return self

    def with_middleware(self, middleware: Callable) -> "EngineBuilder":
        """Add middleware to the authorization pipeline"""
        self._middleware.append(middleware)
        return self

    def build(self) -> "EnhancedEngine":
        """Build the enhanced Engine object"""
        try:
            # Create base engine
            base_engine = Engine(
                policy_set=self._policy_set,
                schema=self._schema,
                entities=self._entities,
                validate=self._validation_config.enabled,
            )

            # Create enhanced engine with additional features
            enhanced_engine = EnhancedEngine(
                base_engine=base_engine,
                cache_config=self._cache_config,
                validation_config=self._validation_config,
                logging_config=self._logging_config,
                middleware=self._middleware,
            )

            logger.info(
                "Engine created via builder",
                extra={
                    "policies_count": len(self._policy_set.policies)
                    if self._policy_set
                    else 0,
                    "entities_count": len(self._entities),
                    "caching_enabled": self._cache_config.enabled
                    if self._cache_config
                    else False,
                    "validation_enabled": self._validation_config.enabled,
                },
            )

            return enhanced_engine

        except Exception as e:
            raise EngineInitializationError(
                reason="Failed to build engine",
                config={
                    "cache_config": self._cache_config.__dict__
                    if self._cache_config
                    else None,
                    "validation_config": self._validation_config.__dict__,
                    "logging_config": self._logging_config.__dict__,
                },
                cause=e,
            )


class EnhancedEngine:
    """
    Enhanced Engine wrapper with additional features like caching, middleware, and async support.

    This class wraps the base Engine with additional functionality without breaking
    the existing API.
    """

    def __init__(
        self,
        base_engine: Engine,
        cache_config: Optional[CacheConfig] = None,
        validation_config: Optional[ValidationConfig] = None,
        logging_config: Optional[LoggingConfig] = None,
        middleware: Optional[List[Callable]] = None,
    ):
        self._base_engine = base_engine
        self._cache_config = cache_config or CacheConfig(enabled=False)
        self._validation_config = validation_config or ValidationConfig()
        self._logging_config = logging_config or LoggingConfig()
        self._middleware = middleware or []

        # Initialize caching if enabled
        self._policy_cache = None
        self._decision_cache = None
        if self._cache_config.enabled:
            self._init_caches()

    def _init_caches(self):
        """Initialize cache structures"""
        try:
            from time import time

            # Simple TTL cache implementation
            class TTLCache:
                def __init__(self, maxsize: int, ttl: int):
                    self.maxsize = maxsize
                    self.ttl = ttl
                    self._cache = {}
                    self._timestamps = {}

                def get(self, key):
                    if key in self._cache:
                        if time() - self._timestamps[key] < self.ttl:
                            return self._cache[key]
                        else:
                            del self._cache[key]
                            del self._timestamps[key]
                    return None

                def set(self, key, value):
                    if len(self._cache) >= self.maxsize:
                        # Remove oldest entry
                        oldest_key = min(
                            self._timestamps.keys(), key=lambda k: self._timestamps[k]
                        )
                        del self._cache[oldest_key]
                        del self._timestamps[oldest_key]

                    self._cache[key] = value
                    self._timestamps[key] = time()

            self._decision_cache = TTLCache(
                maxsize=self._cache_config.decision_cache_size,
                ttl=self._cache_config.decision_ttl_seconds,
            )

            logger.debug(
                "Caching initialized",
                extra={"cache_config": self._cache_config.__dict__},
            )

        except Exception as e:
            logger.warning(f"Failed to initialize caching: {e}")
            self._cache_config.enabled = False

    def is_authorized(
        self,
        principal: Union[Principal, str],
        action: Union[Action, str],
        resource: Union[Resource, str],
        context: Optional[Context] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Enhanced authorization with caching and middleware support.
        Maintains backward compatibility with base Engine API.
        """

        # Generate cache key if caching is enabled
        cache_key = None
        if self._cache_config.enabled and self._decision_cache:
            cache_key = self._generate_cache_key(
                principal, action, resource, context, entities
            )
            cached_result = self._decision_cache.get(cache_key)
            if cached_result is not None:
                logger.debug("Authorization cache hit", extra={"cache_key": cache_key})
                return cached_result

        # Process through middleware
        request_data = {
            "principal": principal,
            "action": action,
            "resource": resource,
            "context": context,
            "entities": entities,
        }

        for middleware in self._middleware:
            try:
                request_data = middleware(request_data) or request_data
            except Exception as e:
                logger.error(f"Middleware error: {e}")
                if self._validation_config.strict_mode:
                    raise

        # Call base engine
        try:
            result = self._base_engine.is_authorized(
                principal=request_data["principal"],
                action=request_data["action"],
                resource=request_data["resource"],
                context=request_data["context"],
                entities=request_data["entities"],
            )

            # Cache the result
            if cache_key and self._decision_cache:
                self._decision_cache.set(cache_key, result)
                logger.debug(
                    "Authorization result cached", extra={"cache_key": cache_key}
                )

            # Audit logging
            if self._logging_config.audit_enabled:
                self._audit_log_authorization(request_data, result)

            return result

        except Exception as e:
            logger.error(
                "Authorization failed",
                extra={
                    "principal": str(principal),
                    "action": str(action),
                    "resource": str(resource),
                    "error": str(e),
                },
            )
            raise

    async def is_authorized_async(
        self,
        principal: Union[Principal, str],
        action: Union[Action, str],
        resource: Union[Resource, str],
        context: Optional[Context] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Async version of is_authorized"""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.is_authorized, principal, action, resource, context, entities
        )

    async def authorize_batch(
        self, requests: List[Dict[str, Any]], concurrency_limit: int = 100
    ) -> List[bool]:
        """Process multiple authorization requests concurrently"""
        semaphore = asyncio.Semaphore(concurrency_limit)

        async def _authorize_single(request: Dict[str, Any]) -> bool:
            async with semaphore:
                return await self.is_authorized_async(**request)

        return await asyncio.gather(*[_authorize_single(req) for req in requests])

    def _generate_cache_key(
        self,
        principal: Union[Principal, str],
        action: Union[Action, str],
        resource: Union[Resource, str],
        context: Optional[Context],
        entities: Optional[Dict[str, Any]],
    ) -> str:
        """Generate a cache key for the authorization request"""
        import hashlib

        # Convert to strings for consistent hashing
        p_str = str(principal)
        a_str = str(action)
        r_str = str(resource)
        c_str = str(context.data if context else {})
        e_str = str(sorted(entities.items()) if entities else {})

        cache_data = f"{p_str}|{a_str}|{r_str}|{c_str}|{e_str}"
        return hashlib.sha256(cache_data.encode()).hexdigest()[:16]

    def _audit_log_authorization(self, request_data: Dict[str, Any], result: bool):
        """Log authorization request for audit purposes"""
        audit_data = {
            "event": "authorization_request",
            "principal": str(request_data["principal"]),
            "action": str(request_data["action"]),
            "resource": str(request_data["resource"]),
            "decision": "ALLOW" if result else "DENY",
            "context": request_data.get("context", {}),
        }

        # Use a separate audit logger
        audit_logger = logging.getLogger(f"{__name__}.audit")
        audit_logger.info("Authorization decision", extra=audit_data)

    def clear_cache(self):
        """Clear all cached data"""
        if self._decision_cache:
            self._decision_cache._cache.clear()
            self._decision_cache._timestamps.clear()
            logger.info("Authorization cache cleared")

    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self._cache_config.enabled or not self._decision_cache:
            return {"enabled": False}

        return {
            "enabled": True,
            "decision_cache_size": len(self._decision_cache._cache),
            "max_decision_cache_size": self._cache_config.decision_cache_size,
            "ttl_seconds": self._cache_config.decision_ttl_seconds,
        }
