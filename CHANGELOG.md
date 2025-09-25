# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive CI/CD pipeline with GitHub Actions
- Performance benchmarking suite 
- Real-world document management system demo
- Pre-commit hooks for code quality
- Enhanced documentation with badges and examples
- Type hints and mypy support

### Changed
- Improved project packaging with better metadata
- Enhanced README with comprehensive examples
- Updated development dependencies

## [0.1.0] - 2024-01-15

### Added
- Initial release of Cedar-Py
- Python bindings for Amazon's Cedar policy language
- Rust backend with PyO3 for native performance
- Core classes: Policy, PolicySet, Engine
- Entity models: Principal, Resource, Action, Context
- Comprehensive test suite with 1,160+ lines of coverage
- Basic usage examples and documentation

### Features
- Load and manage Cedar policies from strings
- Create and manage policy sets
- Make authorization decisions with context support
- Pythonic API for working with Cedar entities
- Native performance through Rust bindings