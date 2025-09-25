"""
Cedar-Py Framework Integrations

This package provides seamless integrations with popular Python frameworks
for drop-in authorization using Cedar policies.

Available integrations:
- FastAPI: Decorator-based authorization for FastAPI applications
- Django: Class-based views and middleware integration (coming soon)
- Flask: Blueprint and decorator integration (coming soon)
"""

# Import integrations that have optional dependencies
__all__ = []

try:
    from .fastapi import CedarPermissionChecker

    __all__.append("CedarPermissionChecker")
except ImportError:
    # FastAPI not available, skip integration
    pass

# Placeholder for future integrations
# try:
#     from .django import CedarDjangoMixin
#     __all__.append('CedarDjangoMixin')
# except ImportError:
#     pass
#
# try:
#     from .flask import CedarFlaskBlueprint
#     __all__.append('CedarFlaskBlueprint')
# except ImportError:
#     pass
