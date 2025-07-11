# Cedar-Py Tests

This directory contains tests for the Cedar-Py library. The tests are designed to verify the functionality of the Python wrapper for Cedar, as well as to provide examples of how to use the library.

## Test Organization

- **test_policy.py**: Tests for the `Policy` and `PolicySet` classes
- **test_engine.py**: Tests for the `Engine` class and basic authorization decisions
- **test_models.py**: Tests for the entity models (`Principal`, `Resource`, `Action`, `Context`)
- **test_migration.py**: Tests demonstrating migration patterns from Vakt to Cedar-Py
- **test_complex.py**: Tests for complex Cedar authorization scenarios

## Running Tests

To run the tests, you need to first build the Cedar-Py package:

```bash
# Build the package in development mode
./build.sh

# Run tests
pytest
```

## Test Dependencies

- pytest
- (optional) vakt - for migration comparison tests

## Writing New Tests

When adding new tests, follow these guidelines:

1. Import Cedar-Py modules inside test functions to avoid import errors when the package is not built:

```python
def test_something():
    from cedar_py import Policy, Engine
    
    # Test code here
```

2. Include comprehensive test cases that demonstrate both successful and failing authorization decisions.

3. Add tests for edge cases and error handling.

4. Use descriptive test names and add docstrings to explain what each test is checking.

## Test Fixtures

Common test fixtures or helper functions can be added in the future to reduce code duplication.

## Test Data Sources

The test scenarios, example use cases, and corpus files in `tests/example_use_cases/` and `tests/corpus-tests/` were originally sourced from the upstream Cedar project and the `cedar-integration-tests` repository. These files were migrated to this directory to ensure full coverage of Cedar syntax, edge cases, and compliance scenarios. See the Cedar project documentation for more details on the original test data and specifications.
