"""
Comprehensive error handling and exception hierarchy for Cedar-Py
"""

from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorCode(Enum):
    """Enumeration of all error codes used in Cedar-Py"""

    # Entity related errors
    ENTITY_VALIDATION_ERROR = "ENTITY_VALIDATION_ERROR"
    ENTITY_PARSE_ERROR = "ENTITY_PARSE_ERROR"

    # Policy related errors
    POLICY_PARSE_ERROR = "POLICY_PARSE_ERROR"
    POLICY_VALIDATION_ERROR = "POLICY_VALIDATION_ERROR"
    POLICY_SYNTAX_ERROR = "POLICY_SYNTAX_ERROR"
    POLICY_NOT_FOUND = "POLICY_NOT_FOUND"
    POLICY_ID_CONFLICT = "POLICY_ID_CONFLICT"

    # Engine related errors
    ENGINE_INITIALIZATION_ERROR = "ENGINE_INITIALIZATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    ENGINE_CONFIGURATION_ERROR = "ENGINE_CONFIGURATION_ERROR"

    # Schema related errors
    SCHEMA_VALIDATION_ERROR = "SCHEMA_VALIDATION_ERROR"
    SCHEMA_PARSE_ERROR = "SCHEMA_PARSE_ERROR"

    # Context related errors
    CONTEXT_VALIDATION_ERROR = "CONTEXT_VALIDATION_ERROR"

    # Cache related errors
    CACHE_ERROR = "CACHE_ERROR"
    CACHE_MISS = "CACHE_MISS"

    # Network/IO errors
    NETWORK_ERROR = "NETWORK_ERROR"
    FILE_IO_ERROR = "FILE_IO_ERROR"

    # Internal errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RUST_BACKEND_ERROR = "RUST_BACKEND_ERROR"


class CedarError(Exception):
    """
    Base exception for Cedar-Py with rich context and structured error information.

    All Cedar-Py exceptions inherit from this class and provide:
    - Structured error codes for programmatic handling
    - Rich context for debugging and logging
    - Chain of causation for error tracing
    - Suggestions for error resolution where applicable
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        suggestions: Optional[List[str]] = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
        self.cause = cause
        self.suggestions = suggestions or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization/logging"""
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "error_code": self.error_code.value,
            "context": self.context,
            "cause": str(self.cause) if self.cause else None,
            "suggestions": self.suggestions,
        }

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.context:
            parts.append(f"Context: {self.context}")
        if self.cause:
            parts.append(f"Caused by: {self.cause}")
        if self.suggestions:
            parts.append(f"Suggestions: {'; '.join(self.suggestions)}")
        return " | ".join(parts)


class EntityValidationError(CedarError):
    """Raised when entity UID validation fails"""

    def __init__(self, uid: str, **kwargs):
        super().__init__(
            f'Invalid entity UID format: "{uid}". Expected \'namespace::"id"\'.',
            ErrorCode.ENTITY_VALIDATION_ERROR,
            context={"uid": uid},
            suggestions=[
                'Use format like User::"alice" or Document::"doc123"',
                'Ensure namespace and ID are separated by "::"',
                "Quote the ID portion with double quotes",
            ],
            **kwargs,
        )


class EntityParseError(CedarError):
    """Raised when entity parsing from dict/JSON fails"""

    def __init__(self, data: Dict[str, Any], reason: str, **kwargs):
        super().__init__(
            f"Failed to parse entity from data: {reason}",
            ErrorCode.ENTITY_PARSE_ERROR,
            context={"data": data, "reason": reason},
            suggestions=[
                'Ensure entity has required "type" and "id" fields',
                "Check that entity data format matches Cedar specification",
            ],
            **kwargs,
        )


class PolicyParseError(CedarError):
    """Raised when policy parsing fails"""

    def __init__(
        self,
        policy_text: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
        **kwargs,
    ):
        location = ""
        if line is not None and column is not None:
            location = f" at line {line}, column {column}"
        elif line is not None:
            location = f" at line {line}"

        super().__init__(
            f"Failed to parse Cedar policy{location}",
            ErrorCode.POLICY_PARSE_ERROR,
            context={
                "policy_text": policy_text[:200] + "..."
                if len(policy_text) > 200
                else policy_text,
                "line": line,
                "column": column,
            },
            suggestions=[
                "Check policy syntax against Cedar language specification",
                "Verify all strings are properly quoted",
                "Ensure proper use of semicolons and braces",
            ],
            **kwargs,
        )


class PolicyValidationError(CedarError):
    """Raised when policy validation fails against schema"""

    def __init__(self, policy_id: str, validation_errors: List[str], **kwargs):
        super().__init__(
            f"Policy '{policy_id}' failed validation: {'; '.join(validation_errors)}",
            ErrorCode.POLICY_VALIDATION_ERROR,
            context={"policy_id": policy_id, "validation_errors": validation_errors},
            suggestions=[
                "Check policy against schema requirements",
                "Verify entity types and actions are properly defined",
                "Ensure attribute references are valid",
            ],
            **kwargs,
        )


class PolicyNotFoundError(CedarError):
    """Raised when a requested policy cannot be found"""

    def __init__(self, policy_id: str, **kwargs):
        super().__init__(
            f"Policy with ID '{policy_id}' not found",
            ErrorCode.POLICY_NOT_FOUND,
            context={"policy_id": policy_id},
            suggestions=[
                "Verify the policy ID is correct",
                "Check that the policy has been loaded into the policy set",
                "Ensure policy was not removed or renamed",
            ],
            **kwargs,
        )


class EngineInitializationError(CedarError):
    """Raised when the Cedar engine fails to initialize"""

    def __init__(self, reason: str, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(
            f"Failed to initialize Cedar engine: {reason}",
            ErrorCode.ENGINE_INITIALIZATION_ERROR,
            context={"reason": reason, "config": config},
            suggestions=[
                "Check engine configuration parameters",
                "Ensure all required policies and schemas are valid",
                "Verify entity data is properly formatted",
            ],
            **kwargs,
        )


class AuthorizationError(CedarError):
    """Raised when authorization request processing fails"""

    def __init__(
        self, principal: str, action: str, resource: str, reason: str, **kwargs
    ):
        super().__init__(
            f"Authorization failed for {principal} -> {action} -> {resource}: {reason}",
            ErrorCode.AUTHORIZATION_ERROR,
            context={
                "principal": principal,
                "action": action,
                "resource": resource,
                "reason": reason,
            },
            suggestions=[
                "Verify principal, action, and resource are properly formatted",
                "Check that relevant policies are loaded",
                "Ensure context data is complete and valid",
            ],
            **kwargs,
        )


class SchemaValidationError(CedarError):
    """Raised when schema validation fails"""

    def __init__(self, schema_errors: List[str], **kwargs):
        super().__init__(
            f"Schema validation failed: {'; '.join(schema_errors)}",
            ErrorCode.SCHEMA_VALIDATION_ERROR,
            context={"schema_errors": schema_errors},
            suggestions=[
                "Check schema syntax against Cedar schema specification",
                "Verify entity types and action definitions",
                "Ensure attribute types are properly declared",
            ],
            **kwargs,
        )


class CacheError(CedarError):
    """Raised when cache operations fail"""

    def __init__(self, operation: str, reason: str, **kwargs):
        super().__init__(
            f"Cache {operation} failed: {reason}",
            ErrorCode.CACHE_ERROR,
            context={"operation": operation, "reason": reason},
            suggestions=[
                "Check cache configuration and connectivity",
                "Verify cache size limits and TTL settings",
                "Consider clearing cache if corruption is suspected",
            ],
            **kwargs,
        )


class RustBackendError(CedarError):
    """Raised when the Rust backend encounters an error"""

    def __init__(self, rust_error: str, operation: str, **kwargs):
        super().__init__(
            f"Rust backend error during {operation}: {rust_error}",
            ErrorCode.RUST_BACKEND_ERROR,
            context={"rust_error": rust_error, "operation": operation},
            suggestions=[
                "This is likely a bug in the Rust backend",
                "Please report this error with full context",
                "Check if input data conforms to expected format",
            ],
            **kwargs,
        )


# Convenience functions for common error scenarios
def policy_syntax_error(policy_text: str, rust_error: str) -> PolicyParseError:
    """Create a PolicyParseError from Rust backend syntax error"""
    return PolicyParseError(
        policy_text=policy_text, cause=RustBackendError(rust_error, "policy parsing")
    )


def authorization_denied(
    principal: str, action: str, resource: str, applied_policies: List[str]
) -> AuthorizationError:
    """Create an AuthorizationError for denied requests"""
    return AuthorizationError(
        principal=principal,
        action=action,
        resource=resource,
        reason="Request denied by policy evaluation",
        context={"applied_policies": applied_policies},
    )


def invalid_entity_format(entity_data: Dict[str, Any]) -> EntityParseError:
    """Create an EntityParseError for malformed entity data"""
    return EntityParseError(
        data=entity_data, reason="Missing required 'type' or 'id' fields"
    )
