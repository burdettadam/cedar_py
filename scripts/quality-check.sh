#!/bin/bash
set -e

echo "🔍 Running Cedar-Py Code Quality Checks"
echo "======================================"

# Change to project root directory
cd "$(dirname "$0")/.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to print info
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Check if virtual environment is activated or UV is managing it
if [[ "$VIRTUAL_ENV" == "" ]] && ! command -v uv >/dev/null 2>&1; then
    print_warning "No virtual environment detected and UV not found. Consider using UV or activating a virtual environment."
elif command -v uv >/dev/null 2>&1; then
    print_info "Using UV for dependency management"
fi

# Install development dependencies if needed
print_info "Checking development dependencies..."
if command -v uv >/dev/null 2>&1; then
    uv sync --dev > /dev/null 2>&1
else
    pip install -e ".[dev]" > /dev/null 2>&1
fi

echo ""
echo "🎨 Code Formatting"
echo "=================="

# Check Black formatting
print_info "Checking Black formatting..."
if command -v uv >/dev/null 2>&1; then
    if uv run black --check --diff cedar_py tests examples; then
        print_status 0 "Black formatting"
    else
        print_status 1 "Black formatting (run 'uv run black cedar_py tests examples' to fix)"
        BLACK_FAILED=1
    fi
else
    if black --check --diff cedar_py tests examples; then
        print_status 0 "Black formatting"
    else
        print_status 1 "Black formatting (run 'black cedar_py tests examples' to fix)"
        BLACK_FAILED=1
    fi
fi

# Check import sorting
print_info "Checking import sorting..."
if command -v uv >/dev/null 2>&1; then
    if uv run isort --check-only --diff cedar_py tests examples; then
        print_status 0 "Import sorting"
    else
        print_status 1 "Import sorting (run 'uv run isort cedar_py tests examples' to fix)"
        ISORT_FAILED=1
    fi
else
    if isort --check-only --diff cedar_py tests examples; then
        print_status 0 "Import sorting"
    else
        print_status 1 "Import sorting (run 'isort cedar_py tests examples' to fix)"
        ISORT_FAILED=1
    fi
fi

echo ""
echo "🔍 Linting"
echo "=========="

# Flake8 linting
print_info "Running flake8..."
if command -v uv >/dev/null 2>&1; then
    if uv run flake8 cedar_py tests examples; then
        print_status 0 "Flake8 linting"
    else
        print_status 1 "Flake8 linting"
        FLAKE8_FAILED=1
    fi
else
    if flake8 cedar_py tests examples; then
        print_status 0 "Flake8 linting"
    else
        print_status 1 "Flake8 linting"
        FLAKE8_FAILED=1
    fi
fi

echo ""
echo "🏷️ Type Checking"
echo "================"

# MyPy type checking
print_info "Running MyPy..."
if command -v uv >/dev/null 2>&1; then
    if uv run mypy cedar_py --ignore-missing-imports; then
        print_status 0 "MyPy type checking"
    else
        print_status 1 "MyPy type checking"
        MYPY_FAILED=1
    fi
else
    if mypy cedar_py --ignore-missing-imports; then
        print_status 0 "MyPy type checking"
    else
        print_status 1 "MyPy type checking"
        MYPY_FAILED=1
    fi
fi

echo ""
echo "🔒 Security Analysis"
echo "==================="

# Bandit security analysis
print_info "Running Bandit security analysis..."
if command -v uv >/dev/null 2>&1; then
    if uv run bandit -r cedar_py -q; then
        print_status 0 "Bandit security scan"
    else
        print_status 1 "Bandit security scan"
        BANDIT_FAILED=1
    fi
else
    if bandit -r cedar_py -q; then
        print_status 0 "Bandit security scan"
    else
        print_status 1 "Bandit security scan"
        BANDIT_FAILED=1
    fi
fi

# Safety dependency check
print_info "Checking dependency security..."
if command -v uv >/dev/null 2>&1; then
    if uv run safety check; then
        print_status 0 "Dependency security"
    else
        print_status 1 "Dependency security"
        SAFETY_FAILED=1
    fi
else
    if safety check; then
        print_status 0 "Dependency security"
    else
        print_status 1 "Dependency security"
        SAFETY_FAILED=1
    fi
fi

echo ""
echo "📊 Code Quality Metrics"
echo "======================="

# Cyclomatic complexity
print_info "Analyzing code complexity..."
echo "Cyclomatic Complexity (showing C grade and above):"
if command -v uv >/dev/null 2>&1; then
    uv run radon cc cedar_py --show-complexity --min C || true
else
    radon cc cedar_py --show-complexity --min C || true
fi

echo ""
echo "Maintainability Index (showing B grade and above):"
if command -v uv >/dev/null 2>&1; then
    uv run radon mi cedar_py --show --min B || true
else
    radon mi cedar_py --show --min B || true
fi

# Dead code detection
print_info "Checking for dead code..."
if command -v uv >/dev/null 2>&1; then
    DEAD_CODE_COUNT=$(uv run vulture cedar_py --min-confidence 80 | wc -l)
    if [ $DEAD_CODE_COUNT -eq 0 ]; then
        print_status 0 "Dead code detection"
    else
        print_warning "Found $DEAD_CODE_COUNT potential dead code instances"
        uv run vulture cedar_py --min-confidence 80
    fi
else
    DEAD_CODE_COUNT=$(vulture cedar_py --min-confidence 80 | wc -l)
    if [ $DEAD_CODE_COUNT -eq 0 ]; then
        print_status 0 "Dead code detection"
    else
        print_warning "Found $DEAD_CODE_COUNT potential dead code instances"
        vulture cedar_py --min-confidence 80
    fi
fi

echo ""
echo "🧪 Test Coverage"
echo "================"

# Run tests with coverage if tests exist
if [ -d "tests" ] && [ "$(ls -A tests)" ]; then
    print_info "Running tests with coverage..."
    if command -v uv >/dev/null 2>&1; then
        if uv run pytest tests/ --cov=cedar_py --cov-report=term-missing --cov-report=html; then
            print_status 0 "Tests and coverage"
        else
            print_status 1 "Tests"
            TESTS_FAILED=1
        fi
    else
        if pytest tests/ --cov=cedar_py --cov-report=term-missing --cov-report=html; then
            print_status 0 "Tests and coverage"
        else
            print_status 1 "Tests"
            TESTS_FAILED=1
        fi
    fi
else
    print_warning "No tests directory found or tests directory is empty"
fi

echo ""
echo "🦀 Rust Quality Checks"
echo "======================"

if [ -d "rust" ]; then
    cd rust
    
    # Rust formatting
    print_info "Checking Rust formatting..."
    if cargo fmt --check; then
        print_status 0 "Rust formatting"
    else
        print_status 1 "Rust formatting (run 'cargo fmt' to fix)"
        RUST_FMT_FAILED=1
    fi
    
    # Rust linting
    print_info "Running Clippy..."
    if cargo clippy --all-targets --all-features -- -D warnings -A clippy::too_many_arguments; then
        print_status 0 "Clippy linting"
    else
        print_status 1 "Clippy linting"
        CLIPPY_FAILED=1
    fi
    
    # Rust security audit
    print_info "Running security audit..."
    if cargo audit; then
        print_status 0 "Security audit"
    else
        print_status 1 "Security audit"
        AUDIT_FAILED=1
    fi
    
    cd ..
fi

echo ""
echo "📋 Summary"
echo "=========="

# Count total issues
TOTAL_ISSUES=0
[ "${BLACK_FAILED:-0}" -eq 1 ] && ((TOTAL_ISSUES++))
[ "${ISORT_FAILED:-0}" -eq 1 ] && ((TOTAL_ISSUES++))
[ "${FLAKE8_FAILED:-0}" -eq 1 ] && ((TOTAL_ISSUES++))
[ "${MYPY_FAILED:-0}" -eq 1 ] && ((TOTAL_ISSUES++))
[ "${BANDIT_FAILED:-0}" -eq 1 ] && ((TOTAL_ISSUES++))
[ "${SAFETY_FAILED:-0}" -eq 1 ] && ((TOTAL_ISSUES++))
[ "${TESTS_FAILED:-0}" -eq 1 ] && ((TOTAL_ISSUES++))
[ "${RUST_FMT_FAILED:-0}" -eq 1 ] && ((TOTAL_ISSUES++))
[ "${CLIPPY_FAILED:-0}" -eq 1 ] && ((TOTAL_ISSUES++))
[ "${AUDIT_FAILED:-0}" -eq 1 ] && ((TOTAL_ISSUES++))

if [ $TOTAL_ISSUES -eq 0 ]; then
    echo -e "${GREEN}🎉 All quality checks passed! Your code is ready for commit.${NC}"
    exit 0
else
    echo -e "${RED}❌ Found $TOTAL_ISSUES quality issues. Please fix them before committing.${NC}"
    echo ""
    echo "Quick fixes:"
    [ "${BLACK_FAILED:-0}" -eq 1 ] && echo "  • Run: black cedar_py tests examples"
    [ "${ISORT_FAILED:-0}" -eq 1 ] && echo "  • Run: isort cedar_py tests examples"
    [ "${RUST_FMT_FAILED:-0}" -eq 1 ] && echo "  • Run: cd rust && cargo fmt"
    exit 1
fi