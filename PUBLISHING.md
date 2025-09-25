# Publishing to PyPI

This guide explains how to publish Cedar-Py to the Python Package Index (PyPI) when ready.

## Prerequisites

1. **Create PyPI accounts**:
   - [PyPI](https://pypi.org/account/register/) (production)
   - [TestPyPI](https://test.pypi.org/account/register/) (testing)

2. **Install publishing tools**:
   ```bash
   pip install twine build
   ```

3. **Configure API tokens** (recommended over passwords):
   - Go to PyPI Account Settings → API tokens
   - Create a token for this project
   - Store in `~/.pypirc`:
   ```ini
   [pypi]
   username = __token__
   password = pypi-your-api-token-here
   
   [testpypi]
   username = __token__
   password = pypi-your-test-api-token-here
   repository = https://test.pypi.org/legacy/
   ```

## Pre-publication Checklist

Before publishing, ensure:

- [ ] **Version number** is updated in `pyproject.toml`
- [ ] **Changelog** is updated with release notes
- [ ] **Tests pass** on all supported platforms
- [ ] **Documentation** is current and accurate
- [ ] **License** and copyright information is correct
- [ ] **Keywords and classifiers** are appropriate
- [ ] **Long description** renders correctly on PyPI

## Publishing Process

### 1. Test on TestPyPI First

```bash
# Build the package
cd rust
maturin build --release --strip

# Upload to TestPyPI
maturin publish --repository testpypi

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ cedar-py
```

### 2. Publish to PyPI

```bash
# Build for release
cd rust
maturin build --release --strip

# Publish to PyPI
maturin publish

# Or upload pre-built wheels
twine upload dist/*
```

### 3. Post-publication

- Tag the release in Git:
  ```bash
  git tag v0.1.0
  git push origin v0.1.0
  ```
- Create a GitHub release with changelog
- Update README installation instructions
- Announce the release

## GitHub Actions Automation

The CI/CD pipeline (`/.github/workflows/ci.yml`) is already configured to:

1. **Build wheels** for multiple platforms on releases
2. **Publish automatically** to PyPI when you create a GitHub release
3. **Test on multiple Python versions** before publishing

To use automated publishing:

1. **Add PyPI API token** to GitHub repository secrets:
   - Go to Settings → Secrets and variables → Actions
   - Add secret named `PYPI_API_TOKEN` with your PyPI token

2. **Create a GitHub release**:
   - This triggers the build and publish workflow
   - Wheels are built for Linux, macOS, and Windows
   - Package is automatically published to PyPI

## Version Management

Use semantic versioning (semver):
- **Major** (1.0.0): Breaking changes
- **Minor** (0.1.0): New features, backward compatible
- **Patch** (0.1.1): Bug fixes, backward compatible

Pre-release versions:
- **Alpha** (0.1.0a1): Early development
- **Beta** (0.1.0b1): Feature complete, testing
- **Release Candidate** (0.1.0rc1): Final testing

## Package Name Considerations

Currently configured as `cedar_py`, but consider:
- **cedar-py**: More common Python convention (hyphenated)
- **py-cedar**: Alternative naming
- **cedar**: If available (simple is better)

Check availability:
```bash
pip search cedar-py  # or check PyPI directly
```

## When to Publish

Consider publishing when:
- [ ] Core functionality is stable
- [ ] Breaking changes are unlikely
- [ ] Documentation is comprehensive
- [ ] Test coverage is adequate (>80%)
- [ ] You're ready to maintain backward compatibility
- [ ] Security considerations have been addressed

## Marketing Your Package

After publishing:
- **Update project README** with PyPI badge
- **Write a blog post** about the project
- **Share on social media** (Twitter, LinkedIn, Reddit)
- **Submit to Python newsletters** and communities
- **Present at meetups** or conferences

## Support and Maintenance

Plan for:
- **Issue tracking**: Respond to GitHub issues promptly
- **Documentation**: Keep examples and docs updated
- **Security**: Monitor for vulnerabilities
- **Compatibility**: Test with new Python versions
- **Deprecation**: Handle breaking changes gracefully