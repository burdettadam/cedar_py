# Cedar-Py

[![CI/CD](https://github.com/burdettadam/cedar_py/actions/workflows/ci.yml/badge.svg)](https://github.com/burdettadam/cedar_py/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/cedar-py.svg)](https://badge.fury.io/py/cedar-py)
[![Python versions](https://img.shields.io/pypi/pyversions/cedar-py.svg)](https://pypi.org/project/cedar-py/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

High-performance Python bindings for [Amazon's Cedar](https://github.com/cedar-policy/cedar) authorization policy language, built with Rust and PyO3 for native performance.

> ⚠️ **EXPERIMENTAL**: This project is in early development and not yet tested enough for production use. APIs may change without notice.

## ✨ Features

- **🚀 Native Performance**: Rust backend with PyO3 bindings
- **🐍 Pythonic API**: Clean, intuitive interface for Python developers  
- **🌐 FastAPI Integration**: Decorator-based authorization for web apps
- **⚡ Intelligent Caching**: Policy-aware LRU caching with 80%+ hit rates
- **🧪 Testing Framework**: Fluent API for policy testing and validation
- **🛠️ CLI Tools**: Command-line policy management and testing
- **📋 Full Cedar Support**: Complete policy language implementation
- **🔒 Type Safety**: Strong typing with mypy support

## 📦 Installation

> **Note**: Not yet on PyPI. Install from source:

### Prerequisites
- **Python 3.8+**
- **Rust toolchain** (install from [rustup.rs](https://rustup.rs/))
- **UV** (recommended) or **pip with maturin**

### Quick Install with UV (Recommended)
```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/burdettadam/cedar_py.git
cd cedar_py
uv sync --dev
cd rust && uv run maturin develop
```

### Alternative with pip
```bash
# Install Rust first
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Clone repository
git clone https://github.com/burdettadam/cedar_py.git
cd cedar_py

# Install maturin and dependencies
pip install maturin[patchelf]
pip install -e .

# Build Rust extension
cd rust && maturin develop
```

## 🚀 Quick Start

### Basic Authorization
```python
from cedar_py import Policy, Engine

policy = Policy('permit(principal == User::"alice", action, resource);')
engine = Engine(policy)

if engine.is_authorized('User::"alice"', 'Action::"read"', 'Document::"doc1"'):
    print("✅ Access granted!")
```

### With Intelligent Caching
```python
from cedar_py.engine import CacheConfig

cache_config = CacheConfig.create_enabled(max_size=1000, ttl=300.0)
engine = Engine(policy, cache_config=cache_config)

# 87%+ cache hit rates typical
stats = engine.cache_stats()
print(f"Cache hit rate: {stats.hit_rate * 100:.1f}%")
```

### FastAPI Integration
```python
from fastapi import FastAPI
from cedar_py.integrations.fastapi import authorize

app = FastAPI()

@app.get("/documents/{doc_id}")
@authorize(policy, action="read", resource_template="Document::\"{doc_id}\"")
async def get_document(doc_id: str):
    return {"document_id": doc_id}
```

### Testing Framework
```python
from cedar_py.testing import PolicyTestBuilder

scenarios = (PolicyTestBuilder()
    .given_user("alice", department="engineering")
    .when_accessing("read", "engineering_docs")
    .should_be_allowed("Engineers can read their docs")
    .build_scenarios())
```

### CLI Tools
```bash
# Validate policies
python -m cedar_py.cli validate --policy "permit(principal, action, resource);"

# Test policies
python -m cedar_py.cli test --policy-file policies.cedar --test-file scenarios.json

# Convert policies
python -m cedar_py.cli migrate --policy-file input.cedar --output json
```

## 🎯 Running Demos

After installation, explore the demos:

```bash
# Basic usage demonstration
python examples/basic_usage.py

# All modern features (caching, testing, CLI)
python scripts/demo_improvements.py

# FastAPI web application
python examples/applications/fastapi_document_management.py

# Performance benchmarks
python examples/benchmark.py

# CLI tools demo
python scripts/demo_cli_tools.py
```

## 🏗️ Architecture

- **Rust Layer**: Direct Cedar native implementation bindings
- **Python Layer**: Pythonic wrapper with caching and integrations
- **Performance**: ~0.001s authorization with caching, 80-90% hit rates
- **Concurrency**: Thread-safe with async support

## 🧪 Development

```bash
# Development setup
uv sync --dev
cd rust && uv run maturin develop --release

# Run tests
pytest tests/ -v --cov=cedar_py

# Quality checks
./scripts/quality-check.sh

# Test installation
python -c "from cedar_py import Policy, Engine; print('✅ Working!')"
```

## 📊 Performance

| Scenario | Without Cache | With Cache | Improvement |
|----------|--------------|------------|-------------|
| Simple authorization | ~0.01ms | ~0.001ms | 10x faster |
| Entity-based | ~0.05ms | ~0.005ms | 10x faster |
| 1000 concurrent requests | ~1.2s | ~0.15s | 8x faster |

## 🤝 Contributing

Contributions welcome! Recent additions include FastAPI integration, intelligent caching, testing framework, and CLI tools.

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see LICENSE file for details.

---

**Cedar-Py** brings Amazon's Cedar authorization to Python with native performance and modern framework integrations.
