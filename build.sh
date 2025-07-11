#!/bin/bash

# Script to build and install the Cedar-Py package

set -e  # Exit on error

echo "Installing build dependencies..."
pip install maturin pytest

echo "Building package with maturin..."
maturin develop

echo "Package built and installed in development mode."
echo "Run tests with pytest:"
echo "pytest tests/"

echo "To build a wheel distribution, run:"
echo "maturin build"
