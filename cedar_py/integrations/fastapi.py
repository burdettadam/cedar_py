"""
FastAPI Integration for Cedar-Py
A production-ready authorization decorator for FastAPI applications.
"""

import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from cedar_py import Engine, Policy, PolicySet
from cedar_py.models import Action, Context, Principal, Resource

logger = logging.getLogger(__name__)

# Optional FastAPI imports - only import if FastAPI is available
try:
    from fastapi import HTTPException, Request

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logger.warning("FastAPI not available. Install with: pip install fastapi")


class CedarAuthError(Exception):
    """Base exception for Cedar authorization errors."""

    pass


class CedarAuth:
    """
    Cedar authorization integration for FastAPI.

    This class provides decorators and utilities to integrate Cedar policy-based
    authorization into FastAPI applications with minimal configuration.
    """

    def __init__(self, engine: Engine, user_loader: Optional[Callable] = None):
        """
        Initialize CedarAuth with a Cedar engine.

        Args:
            engine: Cedar engine instance with policies loaded
            user_loader: Optional function to load user from request
        """
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI is required. Install with: pip install fastapi")

        self.engine = engine
        self.user_loader = user_loader or self._default_user_loader
        logger.info("CedarAuth initialized")

    def require_permission(
        self,
        action: str,
        resource_type: str,
        resource_id_param: Optional[str] = None,
        context_builder: Optional[Callable] = None,
    ):
        """
        Decorator to require a specific permission for an endpoint.

        Args:
            action: The action being performed (e.g., "read", "write")
            resource_type: Type of resource (e.g., "Document", "User")
            resource_id_param: Path parameter name for resource ID
            context_builder: Optional function to build additional context

        Usage:
            @app.get("/documents/{doc_id}")
            @cedar_auth.require_permission("read", "Document", "doc_id")
            async def get_document(doc_id: str):
                return {"document": doc_id}
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract request from function arguments
                request = self._extract_request(args, kwargs)
                if not request:
                    if FASTAPI_AVAILABLE:
                        raise HTTPException(
                            status_code=500,
                            detail="Could not extract request from function arguments",
                        )
                    else:
                        raise CedarAuthError(
                            "Could not extract request from function arguments"
                        )

                try:
                    # Load user from request
                    user = await self._load_user(request)
                    if not user:
                        if FASTAPI_AVAILABLE:
                            raise HTTPException(
                                status_code=401, detail="Authentication required"
                            )
                        else:
                            raise CedarAuthError("Authentication required")

                    # Build authorization entities
                    principal = Principal(
                        uid=f'User::"{getattr(user, "id", "unknown")}"'
                    )
                    action_entity = Action(uid=f'Action::"{action}"')

                    # Get resource ID
                    resource_id = self._get_resource_id(
                        request, resource_id_param, kwargs
                    )
                    resource = Resource(uid=f'{resource_type}::"{resource_id}"')

                    # Build context
                    context_data = {}
                    if context_builder:
                        context_data.update(await context_builder(request, user))

                    # Add default context
                    context_data.update(self._build_default_context(request))
                    context = Context(data=context_data)

                    # Check authorization
                    decision = self.engine.is_authorized(
                        principal, action_entity, resource, context
                    )

                    if not decision:
                        user_id = getattr(user, "id", "unknown")
                        logger.warning(
                            f"Authorization denied for user {user_id} to {action} {resource_type}:{resource_id}"
                        )
                        if FASTAPI_AVAILABLE:
                            raise HTTPException(
                                status_code=403,
                                detail=f"Permission denied: cannot {action} {resource_type}",
                            )
                        else:
                            raise CedarAuthError(
                                f"Permission denied: cannot {action} {resource_type}"
                            )

                    user_id = getattr(user, "id", "unknown")
                    logger.info(
                        f"Authorization granted for user {user_id} to {action} {resource_type}:{resource_id}"
                    )
                    return await func(*args, **kwargs)

                except (HTTPException, CedarAuthError):
                    raise
                except Exception as e:
                    logger.error(f"Authorization error: {e}")
                    if FASTAPI_AVAILABLE:
                        raise HTTPException(
                            status_code=500, detail="Authorization service error"
                        )
                    else:
                        raise CedarAuthError("Authorization service error")

            return wrapper

        return decorator

    def _extract_request(self, args: tuple, kwargs: dict) -> Optional[object]:
        """Extract FastAPI Request object from function arguments."""
        # Check kwargs first
        if "request" in kwargs:
            return kwargs["request"]

        # Check args for Request-like object
        for arg in args:
            if hasattr(arg, "method") and hasattr(arg, "url"):
                return arg

        return None

    def _get_resource_id(
        self, request: object, resource_id_param: Optional[str], kwargs: dict
    ) -> str:
        """Extract resource ID from request path parameters."""
        if resource_id_param:
            # Try kwargs first (function parameters)
            if resource_id_param in kwargs:
                return str(kwargs[resource_id_param])

            # Try path params if available
            if hasattr(request, "path_params") and hasattr(request.path_params, "get"):
                path_params = request.path_params
                if resource_id_param in path_params:
                    return str(path_params[resource_id_param])

        # Fallback: use first path parameter
        if hasattr(request, "path_params") and request.path_params:
            try:
                return str(list(request.path_params.values())[0])
            except (AttributeError, IndexError):
                pass

        return "unknown"

    async def _load_user(self, request: object) -> Optional[object]:
        """Load user from request using the configured user loader."""
        try:
            if self.user_loader:
                return await self.user_loader(request)
            return None
        except Exception as e:
            logger.error(f"Error loading user: {e}")
            return None

    def _default_user_loader(self, request: object) -> Optional[object]:
        """Default user loader - looks for user in request.state."""
        if hasattr(request, "state") and hasattr(request.state, "user"):
            return request.state.user
        return None

    def _build_default_context(self, request: object) -> Dict[str, Any]:
        """Build default context from request information."""
        context = {
            "timestamp": str(__import__("datetime").datetime.utcnow()),
        }

        # Add request details if available
        if hasattr(request, "headers") and hasattr(request.headers, "get"):
            context["request_id"] = request.headers.get("x-request-id", "unknown")
            context["user_agent"] = request.headers.get("user-agent", "")

        if (
            hasattr(request, "client")
            and request.client
            and hasattr(request.client, "host")
        ):
            context["ip_address"] = request.client.host

        if hasattr(request, "method"):
            context["method"] = request.method

        if hasattr(request, "url") and hasattr(request.url, "path"):
            context["path"] = str(request.url.path)

        return context


# Convenience factory function
def create_cedar_auth(
    policies: List[str], user_loader: Optional[Callable] = None
) -> CedarAuth:
    """
    Create a CedarAuth instance with policies.

    Args:
        policies: List of Cedar policy strings
        user_loader: Optional custom user loader function

    Returns:
        Configured CedarAuth instance

    Usage:
        cedar_auth = create_cedar_auth([
            'permit(principal == User::"alice", action == Action::"read", resource);'
        ])
    """
    policy_objects = [Policy(policy_text) for policy_text in policies]

    if len(policy_objects) == 1:
        engine = Engine(policy_objects[0])
    else:
        policy_set = PolicySet()
        for policy in policy_objects:
            policy_set.add(policy)
        engine = Engine(policy_set)

    return CedarAuth(engine, user_loader)


# Example usage documentation
if __name__ == "__main__":
    print(
        """
    Cedar-Py FastAPI Integration
    
    Quick Start:
    
    from fastapi import FastAPI, Request
    from cedar_py.integrations.fastapi import create_cedar_auth
    
    app = FastAPI()
    
    cedar_auth = create_cedar_auth([
        'permit(principal == User::"alice", action == Action::"read", resource);'
    ])
    
    @app.get("/documents/{doc_id}")
    @cedar_auth.require_permission("read", "Document", "doc_id")
    async def get_document(doc_id: str, request: Request):
        return {"document": doc_id}
    """
    )
