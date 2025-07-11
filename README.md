
# Cedar-Py

Python bindings for Cedar, the authorization policy language.

## Overview

Cedar-Py provides Python bindings for [Cedar](https://github.com/cedar-policy/cedar), allowing you to use Cedar's powerful authorization capabilities in your Python applications.
This library is built using Rust and PyO3, providing native performance while offering a Pythonic API.

## Features

- Load and manage Cedar policies from strings or files
- Create and manage policy sets
- Make authorization decisions
- Pythonic API for working with principals, resources, actions, and context
- Native performance through Rust bindings

## Installation

```bash
pip install cedar-py
```

## Usage

See `examples/basic_usage.py` for a full developer guide with runnable examples.

### Basic Authorization

```python
from cedar_py import Policy, Engine
from cedar_py.models import Principal, Resource, Action, Context

# Define a policy (Cedar source syntax)
policy_str = """
permit(
  principal == User::"alice",
  action == Action::"read",
  resource == Document::"doc123"
);
"""
policy = Policy(policy_str)
engine = Engine(policy)

# Check authorization using Cedar UIDs (quoted)
print(engine.is_authorized('User::"alice"', 'Action::"read"', 'Document::"doc123"'))  # True
print(engine.is_authorized('User::"bob"', 'Action::"read"', 'Document::"doc123"'))    # False

# Using model classes (recommended)
alice = Principal('User::"alice"')
read_action = Action('Action::"read"')
doc123 = Resource('Document::"doc123"')
print(engine.is_authorized(alice, read_action, doc123))  # True

```

### Context-Based Authorization

```python
policy_str = """
permit(
  principal == User::"alice",
  action == Action::"read",
  resource == Document::"doc123"
)
when { context.location == "office" };
"""
policy = Policy(policy_str)
engine = Engine(policy)
office_context = Context({"location": "office"})
home_context = Context({"location": "home"})
print(engine.is_authorized('User::"alice"', 'Action::"read"', 'Document::"doc123"', office_context))  # True
print(engine.is_authorized('User::"alice"', 'Action::"read"', 'Document::"doc123"', home_context))   # False
```

### Detailed Authorization Response

```python
response = engine.authorize(alice, read_action, doc123)
print(f"Decision: {response.decision}")  # List of matching policy IDs (e.g., ['policy0'])
print(f"Allowed: {response.allowed}")    # True/False
print(f"Errors: {response.errors}")      # Any Cedar errors
```

**Note:** The `decision` field lists the IDs of policies that matched and permitted the request. If no policy matched, the list is empty (`[]`). This is standard Cedar behavior.


### Working with Policy Sets

```python
from cedar_py import Policy, PolicySet, Engine

# Create policies
policy1 = Policy('permit(principal == User::"alice", action == Action::"read", resource == Document::"doc123");')
policy2 = Policy('permit(principal == User::"bob", action == Action::"write", resource == Document::"doc456");')

# Create a policy set
policy_set = PolicySet()
policy_set.add(policy1)
policy_set.add(policy2)

# Create an engine with the policy set
engine = Engine(policy_set)

# Check authorization
allowed = engine.is_authorized('User::"bob"', 'Action::"write"', 'Document::"doc456"')
print(f"Bob can write doc456: {allowed}")  # True
```


## Cedar Limitations & Error Handling

- Principal wildcards and some advanced context features are not supported by Cedar.
- If you use unsupported features, Cedar-Py will raise a `ValueError`.
- Always use quoted UIDs for entities (e.g., `User::"alice"`).

## Developer Guide & Examples

See `examples/basic_usage.py` for a full, runnable developer guide covering:
- Basic authorization
- Context-based policies
- Detailed responses
- Model class usage

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
