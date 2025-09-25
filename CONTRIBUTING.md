# Contributing to Cedar-Py

We welcome contributions to Cedar-Py! This document provides guidelines for contributing to the project.

> ⚠️ **Note**: This project is experimental and in active development. APIs may change rapidly, and we're focusing on core functionality and stability before considering backward compatibility guarantees.

## 🚀 Getting Started

### Prerequisites

- Python 3.7+
- Rust 1.70+
- Git

### Development Setup

1. Fork and clone the repository:
```bash
git clone https://github.com/yourusername/cedar_py.git
cd cedar_py
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

5. Build the Rust extension:
```bash
cd rust
maturin develop
cd ..
```

## 🧪 Running Tests

Run the test suite:
```bash
pytest tests/ -v
```

Run tests with coverage:
```bash
pytest tests/ -v --cov=cedar_py --cov-report=html
```

## 🎯 Code Quality

We maintain high code quality standards:

- **Formatting**: Black for Python, rustfmt for Rust
- **Linting**: flake8 for Python, clippy for Rust  
- **Type checking**: mypy for Python
- **Pre-commit hooks**: Automatically run on commit

Run quality checks manually:
```bash
# Python
black cedar_py tests examples
isort cedar_py tests examples
flake8 cedar_py tests examples
mypy cedar_py --ignore-missing-imports

# Rust
cd rust
cargo fmt
cargo clippy -- -D warnings
```

## 📝 Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/amazing-feature
   ```

2. **Make your changes**:
   - Write clear, focused commits
   - Add tests for new functionality
   - Update documentation as needed

3. **Ensure quality**:
   ```bash
   # Run tests
   pytest tests/ -v
   
   # Check formatting
   black --check cedar_py tests examples
   isort --check-only cedar_py tests examples
   
   # Type checking
   mypy cedar_py --ignore-missing-imports
   ```

4. **Submit the PR**:
   - Write a clear description
   - Link any related issues
   - Ensure CI passes

## 🐛 Bug Reports

When reporting bugs, please include:

- **Environment**: Python version, OS, Cedar-Py version
- **Reproduction steps**: Minimal code example
- **Expected vs actual behavior**
- **Error messages or stack traces**

Use the bug report template in GitHub Issues.

## 💡 Feature Requests

For new features:

- **Search existing issues** first
- **Describe the use case** and motivation
- **Provide examples** of the desired API
- **Consider implementation complexity**

## 📚 Documentation

Help improve our documentation:

- **README**: Keep examples current and clear
- **Code comments**: Explain complex logic
- **Docstrings**: Follow Google style
- **Examples**: Add real-world use cases

## 🏗️ Architecture

Understanding the codebase:

### Python Layer (`cedar_py/`)
- `engine.py`: Authorization engine wrapper
- `models.py`: Pydantic models for entities
- `policy.py`: Policy and PolicySet classes

### Rust Layer (`rust/src/`)
- `lib.rs`: PyO3 bindings to Cedar
- Exposes Cedar's native functionality to Python

### Tests (`tests/`)
- Comprehensive test suite with 1,160+ lines
- Unit tests, integration tests, and examples
- Test both Python and Rust components

## 🌟 Types of Contributions

We welcome:

- **Bug fixes**: Fix issues in existing functionality
- **Features**: Add new Cedar language features
- **Performance**: Optimize critical paths
- **Documentation**: Improve guides and examples
- **Tests**: Increase coverage and reliability
- **Examples**: Real-world usage demonstrations

## 📋 Coding Standards

### Python
- Follow PEP 8 with Black formatting
- Use type hints where appropriate
- Write docstrings for public APIs
- Keep functions focused and testable

### Rust
- Follow Rust conventions
- Use rustfmt for formatting
- Handle errors appropriately
- Document public functions

### Commit Messages
Follow conventional commits:
```
feat: add support for policy templates
fix: resolve context parsing issue
docs: update installation instructions
test: add integration tests for engine
```

## 🤝 Community

- Be respectful and inclusive
- Help others learn and contribute
- Share knowledge and best practices
- Celebrate contributions of all sizes

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and ideas
- **Code Review**: Learn through the PR process

## 🙏 Recognition

Contributors are recognized in:
- GitHub contributor graphs
- Release notes for significant contributions  
- Special thanks in documentation updates

Thank you for contributing to Cedar-Py! 🎉