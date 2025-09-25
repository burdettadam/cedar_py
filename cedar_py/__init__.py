"""
Cedar-py: A Python interface for the Cedar policy language.
Modernized with builder patterns, async support, and comprehensive error handling.
"""

# Import the Rust extension classes and expose them at the package level
# These are the direct bindings to the Rust code
from ._rust_importer import RustCedarAuthorizer, RustCedarPolicy, RustCedarPolicySet

# Import async API components
from .async_api import (
    AsyncCedarEngine,
    AsyncConfig,
    AsyncEngineBuilder,
    AuthRequest,
    AuthResult,
    BatchResult,
    authorize_single,
    authorize_user_actions,
    temporary_engine,
)

# Import builder patterns and enhanced components
from .builders import (
    CacheConfig,
    EngineBuilder,
    EnhancedEngine,
    LoggingConfig,
    PolicyBuilder,
    ValidationConfig,
)

# Import CLI utilities
from .cli import PolicyMigrator, PolicyTester, PolicyValidator
from .engine import Engine as PyCedarAuthorizer

# Import comprehensive error handling
from .errors import (
    AuthorizationError,
    CedarError,
    EngineInitializationError,
    EntityValidationError,
    ErrorCode,
    PolicyParseError,
    PolicyValidationError,
)
from .models import Action, Context, Entity, Principal, Resource

# Import the Python wrapper classes
from .policy import Policy as PyCedarPolicy
from .policy import PolicySet as PyCedarPolicySet

# Import testing framework
from .testing import (
    PolicyCoverageAnalyzer,
    PolicyTestBuilder,
    PolicyTestCase,
    TestScenario,
)

# For convenience, we can alias the Python wrappers to the simpler names
Policy = PyCedarPolicy
PolicySet = PyCedarPolicySet
Engine = PyCedarAuthorizer


__all__ = [
    # Core classes
    "PyCedarAuthorizer",
    "PyCedarPolicy",
    "PyCedarPolicySet",
    "Policy",
    "PolicySet",
    "Action",
    "Context",
    "Entity",
    "Principal",
    "Resource",
    # Builder patterns
    "EngineBuilder",
    "PolicyBuilder",
    "EnhancedEngine",
    "CacheConfig",
    "ValidationConfig",
    "LoggingConfig",
    # Error classes
    "CedarError",
    "EntityValidationError",
    "PolicyParseError",
    "PolicyValidationError",
    "EngineInitializationError",
    "AuthorizationError",
    "ErrorCode",
    # Async API
    "AsyncCedarEngine",
    "AsyncEngineBuilder",
    "AuthRequest",
    "AuthResult",
    "BatchResult",
    "AsyncConfig",
    "authorize_single",
    "authorize_user_actions",
    "temporary_engine",
    # Testing framework
    "PolicyTestCase",
    "PolicyTestBuilder",
    "TestScenario",
    "PolicyCoverageAnalyzer",
    # CLI utilities
    "PolicyValidator",
    "PolicyTester",
    "PolicyMigrator",
]
