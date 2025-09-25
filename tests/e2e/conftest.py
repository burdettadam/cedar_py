"""
E2E test configuration - no mocking, uses real Cedar backend.
"""

import pytest


def pytest_configure(config):
    """Configure E2E test markers."""
    config.addinivalue_line("markers", "e2e: End-to-end integration tests with real Cedar backend")