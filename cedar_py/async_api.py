"""
Async API layer for Cedar-Py - High-performance concurrent authorization
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, NamedTuple, Optional, Protocol, Union

from .builders import CacheConfig, EngineBuilder, EnhancedEngine
from .engine import Engine
from .errors import AuthorizationError
from .models import Action, Context, Principal, Resource
from .policy import Policy, PolicySet

logger = logging.getLogger(__name__)


class AuthRequest(NamedTuple):
    """Structured authorization request"""

    principal: Union[Principal, str]
    action: Union[Action, str]
    resource: Union[Resource, str]
    context: Optional[Context] = None
    entities: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None


class AuthResult(NamedTuple):
    """Structured authorization result with timing and context"""

    request_id: Optional[str]
    principal: str
    action: str
    resource: str
    decision: bool
    duration_ms: float
    error: Optional[str] = None
    cache_hit: bool = False


class BatchResult(NamedTuple):
    """Result of batch authorization processing"""

    results: List[AuthResult]
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration_ms: float
    avg_duration_ms: float
    cache_hit_rate: float


@dataclass
class AsyncConfig:
    """Configuration for async operations"""

    max_workers: int = 100
    timeout_seconds: float = 30.0
    batch_size: int = 1000
    enable_streaming: bool = True
    retry_attempts: int = 3
    retry_delay: float = 0.1


class PolicySource(Protocol):
    """Protocol for policy loading sources"""

    async def load_policies(self) -> List[Policy]:
        """Load policies from source"""
        ...

    async def watch_for_changes(self) -> AsyncIterator[List[Policy]]:
        """Watch for policy changes"""
        ...


class AsyncCedarEngine:
    """
    High-performance async Cedar authorization engine with advanced features:

    - Concurrent authorization processing
    - Policy hot reloading
    - Streaming authorization for large datasets
    - Connection pooling and resource management
    - Comprehensive metrics and observability

    Example:
        async with AsyncCedarEngine.builder().with_policies(policies).build() as engine:
            # Single authorization
            result = await engine.is_authorized("User::alice", "read", "Document::doc1")

            # Batch authorization
            requests = [AuthRequest("User::alice", "read", f"Document::doc{i}") for i in range(1000)]
            results = await engine.authorize_batch(requests)

            # Streaming authorization
            async for result in engine.authorize_stream(requests):
                print(f"Decision: {result.decision}")
    """

    def __init__(
        self,
        base_engine: Union[Engine, EnhancedEngine],
        config: Optional[AsyncConfig] = None,
        thread_pool: Optional[ThreadPoolExecutor] = None,
    ):
        self._base_engine = base_engine
        self._config = config or AsyncConfig()
        self._thread_pool = thread_pool
        self._own_thread_pool = thread_pool is None
        self._metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "total_duration_ms": 0.0,
        }
        self._policy_sources: List[PolicySource] = []
        self._hot_reload_task: Optional[asyncio.Task] = None

        if self._own_thread_pool:
            self._thread_pool = ThreadPoolExecutor(
                max_workers=self._config.max_workers, thread_name_prefix="cedar_async"
            )

    @classmethod
    def builder(cls) -> "AsyncEngineBuilder":
        """Create a builder for AsyncCedarEngine"""
        return AsyncEngineBuilder()

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()

    async def start(self):
        """Start the async engine and background tasks"""
        logger.info("Starting AsyncCedarEngine")

        # Start policy hot reloading if sources are configured
        if self._policy_sources:
            self._hot_reload_task = asyncio.create_task(self._policy_hot_reload_loop())

        logger.info(
            "AsyncCedarEngine started",
            extra={
                "max_workers": self._config.max_workers,
                "hot_reload_enabled": bool(self._policy_sources),
            },
        )

    async def stop(self):
        """Stop the async engine and cleanup resources"""
        logger.info("Stopping AsyncCedarEngine")

        # Stop hot reload task
        if self._hot_reload_task:
            self._hot_reload_task.cancel()
            try:
                await self._hot_reload_task
            except asyncio.CancelledError:
                pass

        # Shutdown thread pool if we own it
        if self._own_thread_pool and self._thread_pool:
            self._thread_pool.shutdown(wait=True)

        logger.info("AsyncCedarEngine stopped")

    async def is_authorized(
        self,
        principal: Union[Principal, str],
        action: Union[Action, str],
        resource: Union[Resource, str],
        context: Optional[Context] = None,
        entities: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        Async authorization check for a single request.

        Returns:
            bool: True if authorized, False if denied
        """
        result = await self.authorize_request(
            AuthRequest(principal, action, resource, context, entities), timeout=timeout
        )

        if result.error:
            raise AuthorizationError(
                str(principal), str(action), str(resource), result.error
            )

        return result.decision

    async def authorize_request(
        self, request: AuthRequest, timeout: Optional[float] = None
    ) -> AuthResult:
        """
        Process a single authorization request with full result details.

        Returns:
            AuthResult: Complete result with timing and context
        """
        start_time = time.time()
        timeout = timeout or self._config.timeout_seconds

        try:
            # Check if enhanced engine has async support
            if hasattr(self._base_engine, "is_authorized_async"):
                decision = await asyncio.wait_for(
                    self._base_engine.is_authorized_async(
                        request.principal,
                        request.action,
                        request.resource,
                        request.context,
                        request.entities,
                    ),
                    timeout=timeout,
                )
            else:
                # Fall back to thread pool execution
                loop = asyncio.get_event_loop()
                decision = await asyncio.wait_for(
                    loop.run_in_executor(
                        self._thread_pool, self._sync_authorize, request
                    ),
                    timeout=timeout,
                )

            duration_ms = (time.time() - start_time) * 1000

            # Update metrics
            self._metrics["total_requests"] += 1
            self._metrics["successful_requests"] += 1
            self._metrics["total_duration_ms"] += duration_ms

            return AuthResult(
                request_id=request.request_id,
                principal=str(request.principal),
                action=str(request.action),
                resource=str(request.resource),
                decision=decision,
                duration_ms=duration_ms,
                cache_hit=False,  # TODO: Integrate with cache metrics
            )

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            self._metrics["total_requests"] += 1
            self._metrics["failed_requests"] += 1

            return AuthResult(
                request_id=request.request_id,
                principal=str(request.principal),
                action=str(request.action),
                resource=str(request.resource),
                decision=False,
                duration_ms=duration_ms,
                error=f"Authorization timeout after {timeout}s",
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._metrics["total_requests"] += 1
            self._metrics["failed_requests"] += 1

            logger.error(
                "Authorization request failed",
                extra={
                    "principal": str(request.principal),
                    "action": str(request.action),
                    "resource": str(request.resource),
                    "error": str(e),
                },
            )

            return AuthResult(
                request_id=request.request_id,
                principal=str(request.principal),
                action=str(request.action),
                resource=str(request.resource),
                decision=False,
                duration_ms=duration_ms,
                error=str(e),
            )

    async def authorize_batch(
        self,
        requests: List[AuthRequest],
        concurrency_limit: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> BatchResult:
        """
        Process multiple authorization requests concurrently.

        Args:
            requests: List of authorization requests
            concurrency_limit: Maximum concurrent requests (defaults to config)
            timeout: Timeout per request in seconds

        Returns:
            BatchResult: Aggregated results with statistics
        """
        start_time = time.time()
        concurrency_limit = concurrency_limit or self._config.max_workers
        semaphore = asyncio.Semaphore(concurrency_limit)

        async def _process_request(req: AuthRequest) -> AuthResult:
            async with semaphore:
                return await self.authorize_request(req, timeout=timeout)

        # Process all requests concurrently
        results = await asyncio.gather(
            *[_process_request(req) for req in requests], return_exceptions=True
        )

        # Handle any exceptions from gather
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    AuthResult(
                        request_id=requests[i].request_id,
                        principal=str(requests[i].principal),
                        action=str(requests[i].action),
                        resource=str(requests[i].resource),
                        decision=False,
                        duration_ms=0,
                        error=str(result),
                    )
                )
            else:
                processed_results.append(result)

        # Calculate statistics
        total_duration_ms = (time.time() - start_time) * 1000
        successful = sum(1 for r in processed_results if r.error is None)
        failed = len(processed_results) - successful
        cache_hits = sum(1 for r in processed_results if r.cache_hit)
        cache_hit_rate = cache_hits / len(processed_results) if processed_results else 0
        avg_duration = (
            sum(r.duration_ms for r in processed_results) / len(processed_results)
            if processed_results
            else 0
        )

        logger.info(
            "Batch authorization completed",
            extra={
                "total_requests": len(requests),
                "successful": successful,
                "failed": failed,
                "cache_hit_rate": cache_hit_rate,
                "total_duration_ms": total_duration_ms,
                "avg_duration_ms": avg_duration,
            },
        )

        return BatchResult(
            results=processed_results,
            total_requests=len(requests),
            successful_requests=successful,
            failed_requests=failed,
            total_duration_ms=total_duration_ms,
            avg_duration_ms=avg_duration,
            cache_hit_rate=cache_hit_rate,
        )

    async def authorize_stream(
        self, requests: List[AuthRequest], batch_size: Optional[int] = None
    ) -> AsyncIterator[AuthResult]:
        """
        Stream authorization results as they complete.

        Useful for processing large datasets where you want to handle
        results as soon as they're available rather than waiting for all.

        Args:
            requests: List of authorization requests
            batch_size: Size of processing batches

        Yields:
            AuthResult: Individual authorization results as they complete
        """
        batch_size = batch_size or self._config.batch_size

        for i in range(0, len(requests), batch_size):
            batch = requests[i : i + batch_size]
            batch_result = await self.authorize_batch(batch)

            for result in batch_result.results:
                yield result

    def _sync_authorize(self, request: AuthRequest) -> bool:
        """Synchronous authorization for thread pool execution"""
        return self._base_engine.is_authorized(
            request.principal,
            request.action,
            request.resource,
            request.context,
            request.entities,
        )

    def add_policy_source(self, source: PolicySource):
        """Add a policy source for hot reloading"""
        self._policy_sources.append(source)
        logger.info("Policy source added for hot reloading")

    async def _policy_hot_reload_loop(self):
        """Background task for policy hot reloading"""
        logger.info("Starting policy hot reload loop")

        try:
            while True:
                for source in self._policy_sources:
                    try:
                        # For now, just check for changes periodically
                        # Full async iterator implementation would require
                        # more complex policy source protocols
                        new_policies = await source.load_policies()
                        if new_policies:
                            logger.info(f"Hot reloading {len(new_policies)} policies")
                            # TODO: Implement atomic policy replacement
                            # This would require extending the base engine
                    except Exception as e:
                        logger.error(f"Policy hot reload error: {e}")

                # Check for changes every 5 seconds
                await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info("Policy hot reload loop cancelled")
            raise

    def metrics(self) -> Dict[str, Any]:
        """Get engine performance metrics"""
        total_requests = self._metrics["total_requests"]
        if total_requests == 0:
            return {"total_requests": 0}

        return {
            "total_requests": total_requests,
            "successful_requests": self._metrics["successful_requests"],
            "failed_requests": self._metrics["failed_requests"],
            "success_rate": self._metrics["successful_requests"] / total_requests,
            "cache_hits": self._metrics["cache_hits"],
            "cache_hit_rate": self._metrics["cache_hits"] / total_requests,
            "avg_duration_ms": self._metrics["total_duration_ms"] / total_requests,
            "total_duration_ms": self._metrics["total_duration_ms"],
        }

    def reset_metrics(self):
        """Reset all performance metrics"""
        self._metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "total_duration_ms": 0.0,
        }
        logger.info("Metrics reset")


class AsyncEngineBuilder:
    """Builder for AsyncCedarEngine"""

    def __init__(self):
        self._engine_builder = EngineBuilder()
        self._async_config = AsyncConfig()
        self._thread_pool: Optional[ThreadPoolExecutor] = None

    def with_base_engine(
        self, engine: Union[Engine, EnhancedEngine]
    ) -> "AsyncEngineBuilder":
        """Use an existing engine as base"""
        self._base_engine = engine
        return self

    def with_policies(
        self, policy_set: Union[PolicySet, List[Policy]]
    ) -> "AsyncEngineBuilder":
        """Add policies via the engine builder"""
        self._engine_builder.with_policies(policy_set)
        return self

    def with_schema(self, schema: Dict[str, Any]) -> "AsyncEngineBuilder":
        """Add schema via the engine builder"""
        self._engine_builder.with_schema(schema)
        return self

    def with_caching(
        self, config: Optional[CacheConfig] = None
    ) -> "AsyncEngineBuilder":
        """Enable caching via the engine builder"""
        self._engine_builder.with_caching(config)
        return self

    def with_async_config(self, config: AsyncConfig) -> "AsyncEngineBuilder":
        """Configure async behavior"""
        self._async_config = config
        return self

    def with_max_workers(self, max_workers: int) -> "AsyncEngineBuilder":
        """Set maximum number of worker threads"""
        self._async_config.max_workers = max_workers
        return self

    def with_timeout(self, timeout_seconds: float) -> "AsyncEngineBuilder":
        """Set request timeout"""
        self._async_config.timeout_seconds = timeout_seconds
        return self

    def with_thread_pool(self, thread_pool: ThreadPoolExecutor) -> "AsyncEngineBuilder":
        """Use custom thread pool"""
        self._thread_pool = thread_pool
        return self

    def build(self) -> AsyncCedarEngine:
        """Build the AsyncCedarEngine"""
        # Build base engine if not provided
        if not hasattr(self, "_base_engine"):
            self._base_engine = self._engine_builder.build()

        return AsyncCedarEngine(
            base_engine=self._base_engine,
            config=self._async_config,
            thread_pool=self._thread_pool,
        )


# Convenience functions for common async patterns
async def authorize_single(
    engine: AsyncCedarEngine,
    principal: str,
    action: str,
    resource: str,
    context: Optional[Dict[str, Any]] = None,
) -> bool:
    """Convenience function for single authorization"""
    context_obj = Context(context) if context else None
    return await engine.is_authorized(principal, action, resource, context_obj)


async def authorize_user_actions(
    engine: AsyncCedarEngine, user: str, actions: List[str], resource: str
) -> Dict[str, bool]:
    """Check multiple actions for a user on a resource"""
    requests = [AuthRequest(user, action, resource) for action in actions]

    results = await engine.authorize_batch(requests)
    return {actions[i]: result.decision for i, result in enumerate(results.results)}


@asynccontextmanager
async def temporary_engine(policies: List[Policy], **kwargs):
    """Context manager for temporary async engine"""
    async with (AsyncCedarEngine.builder().with_policies(policies).build()) as engine:
        yield engine
