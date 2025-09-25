# Code Quality Guidelines

This document outlines the code quality standards and tools used in Cedar-Py.

## 🎯 Quality Standards

Cedar-Py maintains high code quality standards to ensure:
- **Reliability**: Code works correctly and consistently
- **Maintainability**: Code is easy to understand, modify, and extend
- **Security**: Code is free from vulnerabilities and follows security best practices
- **Performance**: Code is efficient and scalable
- **Readability**: Code is well-documented and follows consistent style

## 🛠️ Quality Tools

### Code Formatting
- **Black**: Automatic Python code formatting
- **isort**: Import sorting and organization
- **rustfmt**: Rust code formatting

### Linting
- **flake8**: Python linting with style and complexity checks
- **clippy**: Rust linting and best practices

### Type Safety
- **MyPy**: Static type checking for Python
- **Rust compiler**: Built-in type safety for Rust code

### Security Analysis
- **Bandit**: Security vulnerability scanner for Python
- **Safety**: Dependency vulnerability checker
- **cargo audit**: Rust dependency security audit

### Code Quality Metrics
- **Radon**: Cyclomatic complexity and maintainability index
- **Vulture**: Dead code detection
- **Xenon**: Code complexity monitoring

### Test Coverage
- **pytest-cov**: Test coverage measurement
- **Coverage.py**: Coverage reporting and analysis

## 📊 Quality Thresholds

### Required Standards
- **Test Coverage**: ≥ 80%
- **Cyclomatic Complexity**: ≤ 10 per function
- **Maintainability Index**: ≥ 20 (B grade or better)
- **Security Issues**: 0 high-severity issues
- **Linting**: 0 errors, ≤ 10 warnings

### Code Review Standards
- All code must pass automated quality checks
- Complex functions (complexity > 7) require documentation
- Security-sensitive code requires extra review
- Performance-critical code requires benchmarks

## 🚀 Running Quality Checks

### Local Development
```bash
# Run comprehensive quality check
./scripts/quality-check.sh

# Individual tools
black cedar_py tests examples
isort cedar_py tests examples
flake8 cedar_py tests examples
mypy cedar_py
bandit -r cedar_py
safety check
pytest --cov=cedar_py

# Rust checks
cd rust
cargo fmt --check
cargo clippy -- -D warnings
cargo audit
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pre-commit install

# Run all hooks
pre-commit run --all-files

# Run quality check manually
pre-commit run quality-check --hook-stage manual
```

### CI/CD Pipeline
Quality checks run automatically on:
- Every pull request
- Every push to main/develop branches
- Release builds

## 📈 Quality Reports

### GitHub Actions
- **Code Quality Report**: Comprehensive analysis on every PR
- **Coverage Reports**: Uploaded to Codecov
- **Security Scans**: Integrated into CI pipeline

### Artifacts
Quality reports are available as workflow artifacts:
- HTML coverage reports
- Flake8 HTML reports
- MyPy type checking reports
- Security scan results
- Complexity analysis

## 🎨 Code Style Guidelines

### Python
- Follow PEP 8 with Black formatting
- Use type hints for all public APIs
- Document all public functions and classes
- Keep functions focused and testable
- Maximum line length: 88 characters

### Rust
- Follow Rust conventions and idioms
- Use rustfmt for consistent formatting
- Handle errors appropriately with Result types
- Document public functions with doc comments
- Use clippy suggestions to improve code quality

### Documentation
- Use Google-style docstrings for Python
- Include examples in docstrings for complex functions
- Keep README and docs up to date
- Document breaking changes in CHANGELOG

## 🔧 Configuration Files

### Python Tools
- **pyproject.toml**: MyPy, coverage, and tool configuration
- **setup.cfg**: Flake8 configuration
- **.pre-commit-config.yaml**: Pre-commit hook configuration

### Quality Thresholds
```toml
[tool.coverage.report]
fail_under = 80
show_missing = true

[tool.mypy]
strict = true
warn_return_any = true

[tool.bandit]
exclude_dirs = ["tests"]
```

## 🚨 Quality Gates

### Pull Request Requirements
- All quality checks must pass
- Test coverage must not decrease
- No high-severity security issues
- Code review approval required

### Release Requirements
- 100% test coverage for new features
- All quality metrics above thresholds
- Security audit complete
- Performance benchmarks updated

## 📚 Best Practices

### Writing Quality Code
1. **Test first**: Write tests before implementing features
2. **Keep it simple**: Prefer simple, readable solutions
3. **Document intent**: Explain why, not just what
4. **Handle errors**: Always handle potential failures
5. **Profile performance**: Measure before optimizing

### Code Review Focus
1. **Correctness**: Does the code work as intended?
2. **Security**: Are there any security implications?
3. **Performance**: Will this impact system performance?
4. **Maintainability**: Is the code easy to understand and modify?
5. **Testing**: Are there adequate tests for the changes?

### Continuous Improvement
- Regularly review and update quality standards
- Monitor quality metrics trends
- Refactor code that falls below standards
- Update tools and configurations as needed
- Share quality learnings with the team

## 🤝 Contributing to Quality

### Reporting Quality Issues
- Use the Code Quality issue template
- Include relevant metrics and tool output
- Suggest specific improvements
- Label with appropriate priority

### Improving Quality Tools
- Suggest new tools or configurations
- Share quality insights and learnings
- Contribute to quality documentation
- Help maintain CI/CD pipelines

Quality is everyone's responsibility. By following these guidelines and using these tools, we ensure Cedar-Py remains a high-quality, maintainable, and secure project.