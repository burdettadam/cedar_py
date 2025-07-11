"""
Cedar-py: A Python interface for the Cedar policy language.
"""

# Import the Rust extension classes and expose them at the package level
# These are the direct bindings to the Rust code
from ._rust_importer import (
    RustCedarPolicy,
    RustCedarPolicySet,
    RustCedarAuthorizer,
)

# Import the Python wrapper classes
from .policy import Policy as PyCedarPolicy, PolicySet as PyCedarPolicySet
from .engine import Engine as PyCedarAuthorizer
from .models import Entity, Action, Context

# For convenience, we can alias the Python wrappers to the simpler names
Policy = PyCedarPolicy
PolicySet = PyCedarPolicySet
Engine = PyCedarAuthorizer


__all__ = [
    "Policy",
    "PolicySet",
    "Engine",
    "Entity",
    "Action",
    "Context",
    # Expose the Python wrappers with a Py prefix for clarity
    "PyCedarPolicy",
    "PyCedarPolicySet",
    "PyCedarAuthorizer",
    # Expose the raw Rust bindings as well
    "RustCedarPolicy",
    "RustCedarPolicySet",
    "RustCedarAuthorizer",
]
