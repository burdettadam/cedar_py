# Testing Strategy Documentation

## Overview

Cedar-Py now implements a comprehensive two-tier testing strategy that separates **unit tests** (testing Python wrapper logic) from **end-to-end tests** (testing real Cedar integration). This approach provides fast, reliable unit testing while maintaining essential integration validation.

## Test Structure

```
tests/
├── unit/                    # Unit tests with comprehensive mocking
│   ├── conftest.py         # Shared mocks and fixtures  
│   ├── test_basic.py       # Basic wrapper functionality
│   ├── test_complex.py     # Complex scenarios
│   ├── test_engine.py      # Engine authorization logic
│   ├── test_integration.py # Integration patterns (mocked)
│   ├── test_migration.py   # Migration scenarios
│   ├── test_models.py      # Data models and builders
│   └── test_policy.py      # Policy management
└── e2e/                    # End-to-end integration tests
    ├── conftest.py         # E2E test configuration (no mocking)
    └── test_integration.py # Essential integration tests
```

## Unit Tests (tests/unit/)

### Purpose
- Test Cedar-Py Python wrapper logic without Cedar backend dependencies
- Validate data models, builders, error handling, and API flow
- Provide fast, reliable testing for development workflow

### Key Features
- **Comprehensive Mocking**: All Cedar Rust backend calls are mocked
- **Fast Execution**: Run in milliseconds without external dependencies
- **High Coverage**: 56 tests covering all major functionality
- **Predictable Results**: Mocked responses ensure consistent test behavior

### Mock System
The unit test suite uses sophisticated mocks that simulate Cedar behavior:

- **MockCedarAuthorizer**: Simulates authorization decisions
- **MockCedarPolicy**: Mocks policy creation and validation
- **MockCedarPolicySet**: Mocks policy set operations
- **Automatic Import Patching**: Seamlessly replaces Cedar imports

### Running Unit Tests
```bash
# Run all unit tests (fast)
uv run pytest tests/unit/ -v

# Run with coverage
uv run pytest tests/unit/ --cov=cedar_py

# Run specific test file
uv run pytest tests/unit/test_engine.py -v
```

## End-to-End Tests (tests/e2e/)

### Purpose
- Validate real Cedar backend integration
- Ensure actual Cedar policy evaluation works correctly
- Test critical user workflows end-to-end

### Key Features
- **Real Cedar Backend**: Uses actual Rust Cedar library
- **Essential Coverage**: 5 critical integration scenarios
- **True Validation**: Verifies real policy evaluation and authorization
- **Minimal Overhead**: Small focused test suite for efficiency

### Test Cases
1. **Simple Policy Evaluation**: Basic permit/deny decisions
2. **Context-Based Policies**: Authorization with context data
3. **Multiple Policies**: Policy set management and evaluation
4. **Error Handling**: Invalid policy syntax and edge cases
5. **JSON Policy Conversion**: Policy format conversions

### Running E2E Tests
```bash
# Run all E2E tests
uv run pytest tests/e2e/ -v

# Run specific E2E test
uv run pytest tests/e2e/test_integration.py::TestCedarIntegrationE2E::test_simple_policy_evaluation -v
```

## Test Configuration

### Intelligent Mocking System
The test configuration automatically detects test type and applies appropriate mocking:

```python
# tests/conftest.py - Main configuration
@pytest.fixture(autouse=True)
def setup_cedar_mocks(request):
    """Auto-apply mocks for unit tests, skip for E2E tests"""
    # Skip mocking for E2E tests marked with @pytest.mark.e2e
    if request.node.get_closest_marker("e2e"):
        yield
        return
    
    # Apply comprehensive mocking for unit tests
    # ... mock setup code
```

### Test Markers
- **Unit Tests**: No special markers required (default behavior)
- **E2E Tests**: Use `@pytest.mark.e2e` to skip mocking

## Development Workflow

### When to Use Unit Tests
- Testing new wrapper functionality
- Validating data models and builders
- Testing error handling and edge cases
- Rapid development and debugging
- CI/CD pipeline testing

### When to Use E2E Tests
- Validating real Cedar policy evaluation
- Testing critical user workflows
- Ensuring Cedar backend integration works
- Pre-release validation
- Customer-facing scenario verification

### Adding New Tests

#### Adding Unit Tests
```python
# tests/unit/test_new_feature.py
def test_new_feature_logic():
    """Test the wrapper logic without Cedar dependencies"""
    # Cedar calls are automatically mocked
    result = new_feature_function()
    assert result.expected_behavior
```

#### Adding E2E Tests
```python
# tests/e2e/test_integration.py
@pytest.mark.e2e
def test_new_integration_scenario():
    """Test real Cedar backend integration"""
    # Uses real Cedar Rust library
    policy = Policy("permit(principal, action, resource);")
    result = engine.is_authorized("User::\"alice\"", "Action::\"read\"", "Document::\"doc1\"")
    assert result is True
```

## Test Results

### Current Status
- **Unit Tests**: 56/56 passing (100% success rate)
- **E2E Tests**: 5/5 passing (100% success rate)
- **Total Coverage**: Comprehensive wrapper testing + essential integration validation

### Performance Comparison
- **Unit Tests**: ~70ms total (fast development feedback)
- **E2E Tests**: ~40ms total (efficient integration validation)

## Benefits

### Developer Experience
- **Fast Feedback**: Unit tests provide immediate validation
- **Reliable Testing**: Mocked dependencies eliminate external failures
- **Clear Separation**: Easy to understand unit vs integration concerns
- **Flexible Development**: Can develop without Cedar backend setup

### Quality Assurance
- **Comprehensive Coverage**: All wrapper logic thoroughly tested
- **Integration Confidence**: Essential workflows validated end-to-end
- **Regression Prevention**: Both levels catch different types of issues
- **Production Readiness**: Dual validation ensures robust deployments

## Migration from Previous Approach

### Before
- Cedar-dependent tests required real backend for all scenarios
- Slower test execution and unreliable CI/CD
- Mixed unit/integration concerns in single test suite
- Complex test setup requirements

### After
- Clear separation of concerns with appropriate testing strategy
- Fast unit tests with reliable mocking system
- Essential E2E tests for integration confidence
- Simplified test execution and maintenance

## Troubleshooting

### Unit Test Issues
- Verify mocks are properly configured in `tests/unit/conftest.py`
- Check that test doesn't require real Cedar behavior
- Ensure test focuses on wrapper logic, not Cedar functionality

### E2E Test Issues
- Verify `@pytest.mark.e2e` marker is present
- Check that Cedar backend is properly built and accessible
- Ensure test policies have unique IDs to avoid Cedar conflicts

### Build Issues
- Run `./build.sh` to rebuild Cedar Rust components
- Check that all dependencies are properly installed
- Verify Rust toolchain is available and up-to-date

## Best Practices

### Unit Test Guidelines
1. Focus on testing wrapper logic and Python-specific behavior
2. Use mocks to simulate Cedar responses for predictable testing
3. Test error handling and edge cases thoroughly
4. Keep tests fast and independent of external dependencies

### E2E Test Guidelines
1. Test only essential user workflows and integration points
2. Use real Cedar policies with unique IDs to avoid conflicts
3. Focus on critical paths that users actually execute
4. Keep the E2E suite minimal but comprehensive for key scenarios

### Maintenance
1. Regularly review test coverage and effectiveness
2. Update mocks when Cedar API changes
3. Add E2E tests only for new critical integration scenarios
4. Keep documentation current with testing strategy changes

This two-tier testing approach ensures Cedar-Py maintains high quality while providing excellent developer experience and confidence in production deployments.