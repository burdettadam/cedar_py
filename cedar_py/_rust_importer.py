"""
This module handles the dynamic import of the Rust extension `_rust`.

It tries to import the compiled Rust extension `_rust`. If the import fails,
it provides mock objects that will raise an `ImportError` at runtime,
making it clear that the extension is not available.
"""

try:
    # Attempt to import the compiled Rust extension
    from . import _rust
    
    # The Rust extension exports classes named CedarPolicy, CedarPolicySet, etc.
    # We alias them here to avoid name clashes with our Python models and to
    # follow the convention of prefixing the raw bindings with "Rust".
    RustCedarPolicy = _rust.CedarPolicy
    RustCedarPolicySet = _rust.CedarPolicySet
    RustCedarAuthorizer = _rust.CedarAuthorizer

except ImportError:
    # If the import fails, it likely means the Rust extension has not been built.
    # We create mock classes that will raise an informative error if used.
    
    class MockRustClass:
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "The Cedar-py Rust extension is not installed or failed to import. "
                "Please run 'maturin develop' or 'pip install .' to build it."
            )

    RustCedarPolicy = MockRustClass
    RustCedarPolicySet = MockRustClass
    RustCedarAuthorizer = MockRustClass

__all__ = ["RustCedarPolicy", "RustCedarPolicySet", "RustCedarAuthorizer"]
